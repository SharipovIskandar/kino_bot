import asyncio
from datetime import datetime, timezone
from typing import List, Optional

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter, TelegramBadRequest
from loguru import logger
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import (
    BroadcastMessage, BroadcastStatus, BroadcastTarget,
    MediaType, User, Language,
)


async def get_target_user_ids(
    session: AsyncSession,
    target: BroadcastTarget,
) -> List[int]:
    """Target ga qarab user Telegram ID larini olish"""
    from datetime import timedelta

    q = select(User.telegram_id).where(User.is_banned == False, User.is_active == True)

    if target == BroadcastTarget.ACTIVE_7D:
        since = datetime.now(timezone.utc) - timedelta(days=7)
        q = q.where(User.last_active_at >= since)

    elif target == BroadcastTarget.ACTIVE_30D:
        since = datetime.now(timezone.utc) - timedelta(days=30)
        q = q.where(User.last_active_at >= since)

    elif target == BroadcastTarget.LANG_UZ:
        q = q.where(User.language == Language.UZ)

    elif target == BroadcastTarget.LANG_RU:
        q = q.where(User.language == Language.RU)

    elif target == BroadcastTarget.LANG_EN:
        q = q.where(User.language == Language.EN)

    result = await session.execute(q)
    return [row[0] for row in result.all()]


async def run_broadcast(
    bot: Bot,
    session: AsyncSession,
    broadcast: BroadcastMessage,
    user_ids: List[int],
    progress_callback=None,
) -> BroadcastMessage:
    """
    Broadcast xabarini yuborish.
    Telegram rate limit: 30 msg/sec — biz 25 ta/sek yuboramiz.

    Args:
        progress_callback: async funksiya (sent, total) — progress bildirish uchun
    """
    total = len(user_ids)
    sent = 0
    failed = 0

    # DB'ni yangilash — running
    broadcast.status = BroadcastStatus.RUNNING
    broadcast.started_at = datetime.now(timezone.utc)
    broadcast.total_users = total
    await session.commit()

    logger.info(f"Broadcast #{broadcast.id} boshlandi. Jami: {total} user")

    for i, user_id in enumerate(user_ids):
        try:
            await _send_to_user(bot, user_id, broadcast)
            sent += 1
        except TelegramForbiddenError:
            # User botni block qilgan — nofaol qilamiz
            await session.execute(
                update(User)
                .where(User.telegram_id == user_id)
                .values(is_active=False)
            )
            failed += 1
        except TelegramRetryAfter as e:
            # Rate limit — kutamiz
            logger.warning(f"Rate limit! {e.retry_after}s kutilyapti...")
            await asyncio.sleep(e.retry_after)
            try:
                await _send_to_user(bot, user_id, broadcast)
                sent += 1
            except Exception:
                failed += 1
        except Exception as e:
            logger.error(f"User {user_id} ga yuborishda xatolik: {e}")
            failed += 1

        # Progress callback — har 50 ta xabarda
        if progress_callback and (i + 1) % 50 == 0:
            try:
                await progress_callback(sent + failed, total)
            except Exception:
                pass

        # Rate limiting — ~25 msg/sec
        await asyncio.sleep(0.04)

        # DB ni har 100 ta xabarda yangilaymiz
        if (i + 1) % 100 == 0:
            broadcast.total_sent = sent
            broadcast.total_failed = failed
            await session.commit()

    # Yakuniy yangilash
    broadcast.status = BroadcastStatus.DONE
    broadcast.total_sent = sent
    broadcast.total_failed = failed
    broadcast.finished_at = datetime.now(timezone.utc)
    await session.commit()

    logger.info(
        f"Broadcast #{broadcast.id} yakunlandi. "
        f"Yuborildi: {sent}, Xato: {failed}"
    )

    return broadcast


async def _send_to_user(
    bot: Bot,
    user_id: int,
    broadcast: BroadcastMessage,
) -> None:
    """Bitta usergа xabar yuborish"""
    text = broadcast.text or ""
    file_id = broadcast.media_file_id
    media_type = broadcast.media_type

    if media_type == MediaType.PHOTO and file_id:
        await bot.send_photo(chat_id=user_id, photo=file_id, caption=text)
    elif media_type == MediaType.VIDEO and file_id:
        await bot.send_video(chat_id=user_id, video=file_id, caption=text)
    elif media_type == MediaType.DOCUMENT and file_id:
        await bot.send_document(chat_id=user_id, document=file_id, caption=text)
    elif media_type == MediaType.ANIMATION and file_id:
        await bot.send_animation(chat_id=user_id, animation=file_id, caption=text)
    else:
        # Faqat matn
        await bot.send_message(chat_id=user_id, text=text)

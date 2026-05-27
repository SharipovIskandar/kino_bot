import asyncio
from datetime import datetime, timezone

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import settings
from bot.database.crud.movie import upsert_movie
from bot.database.models import SyncLog, SyncStatus
from bot.services.caption_parser import parse_caption

# Ketma-ket topilmagan xabarlar limiti — shundan keyin sync to'xtatiladi
_MAX_CONSECUTIVE_FAILS = 50
# Probe qilinadigan maksimal message_id
_MAX_MSG_ID = 100_000


async def sync_movies_from_channel(
    bot: Bot,
    session: AsyncSession,
    triggered_by: int,
) -> SyncLog:
    """
    Kino kanalidan barcha kinolarni DB'ga sync qiladi.

    Jarayon:
    1. Har bir message_id uchun forward_message orqali xabarni admin chatiga yuboradi
    2. Caption'ni parse qilib kinoni DB'ga upsert qiladi
    3. Forward qilingan xabarni admin chatidan o'chiradi
    4. 50 ta ketma-ket topilmagan message_id kelsa to'xtatiladi
    5. Sync natijasini SyncLog'ga yozadi

    Eslatma: Bot API kanaldan tarix o'qishni qo'llab-quvvatlamaydi, shuning
    uchun biz forward_message "probe" usulidan foydalanamiz. Admin chatida
    xabarlar bir zumga ko'rinib, darhol o'chiriladi.
    """
    sync_log = SyncLog(
        status=SyncStatus.RUNNING,
        triggered_by=triggered_by,
    )
    session.add(sync_log)
    await session.commit()
    await session.refresh(sync_log)

    added = 0
    updated = 0
    skipped = 0
    error_msg = None

    try:
        logger.info(f"Sync boshlandi. Kanal: {settings.movie_channel_id}, admin: {triggered_by}")

        msg_id = 1
        consecutive_fails = 0

        while msg_id <= _MAX_MSG_ID:
            try:
                forwarded = await bot.forward_message(
                    chat_id=triggered_by,
                    from_chat_id=settings.movie_channel_id,
                    message_id=msg_id,
                )
                consecutive_fails = 0

                # Forward qilingan xabarni admin chatidan darhol o'chirish
                try:
                    await bot.delete_message(
                        chat_id=triggered_by,
                        message_id=forwarded.message_id,
                    )
                except Exception:
                    pass

                caption = forwarded.caption or forwarded.text
                photo_file_id = forwarded.photo[-1].file_id if forwarded.photo else None

                if caption:
                    parsed = parse_caption(caption, msg_id)
                    if parsed:
                        _, created = await upsert_movie(
                            session=session,
                            code=parsed.code,
                            channel_message_id=msg_id,
                            title_uz=parsed.title_uz,
                            title_ru=parsed.title_ru,
                            title_en=parsed.title_en,
                            description_uz=parsed.description_uz,
                            description_ru=parsed.description_ru,
                            description_en=parsed.description_en,
                            year=parsed.year,
                            duration=parsed.duration,
                            country=parsed.country,
                            director=parsed.director,
                            cast=parsed.cast,
                            imdb_rating=parsed.imdb_rating,
                            kinopoisk_rating=parsed.kinopoisk_rating,
                            age_rating=parsed.age_rating,
                            poster_file_id=photo_file_id,
                        )
                        if created:
                            added += 1
                        else:
                            updated += 1
                    else:
                        skipped += 1
                else:
                    skipped += 1

            except TelegramBadRequest:
                consecutive_fails += 1
                if consecutive_fails >= _MAX_CONSECUTIVE_FAILS:
                    logger.info(
                        f"Sync: {_MAX_CONSECUTIVE_FAILS} ta ketma-ket topilmadi — "
                        f"to'xtatildi (oxirgi msg_id={msg_id})"
                    )
                    break

            msg_id += 1
            await asyncio.sleep(0.05)

        sync_log.status = SyncStatus.DONE

    except Exception as e:
        logger.error(f"Sync xatolik: {e}")
        sync_log.status = SyncStatus.FAILED
        sync_log.error_message = str(e)
        error_msg = str(e)

    finally:
        sync_log.movies_added = added
        sync_log.movies_updated = updated
        sync_log.movies_skipped = skipped
        sync_log.finished_at = datetime.now(timezone.utc)
        await session.commit()

        logger.info(
            f"Sync yakunlandi: added={added}, updated={updated}, skipped={skipped}"
        )

    return sync_log

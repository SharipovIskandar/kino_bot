from typing import List

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest
from loguru import logger

from bot.database.models import MandatoryChannel

# Obuna hisoblangan statuslar
_SUBSCRIBED_STATUSES = {"member", "administrator", "creator"}


async def check_user_subscriptions(
    bot: Bot,
    user_id: int,
    channels: List[MandatoryChannel],
) -> List[MandatoryChannel]:
    """
    Foydalanuvchining har bir majburiy kanalga obunasini real-time tekshiradi
    (Telegram API get_chat_member orqali, DB cache'siz).

    Returns: Obuna bo'lmagan kanallar ro'yxati (bo'sh ro'yxat = hammasi obuna)
    """
    not_subscribed = []

    for channel in channels:
        # Fake ID li join-request kanallar (channel_id < 0 va kichik raqam)
        # tekshirib bo'lmaydi — shunchaki o'tkazib yuboramiz
        if _is_fake_channel_id(channel.channel_id):
            continue

        try:
            member = await bot.get_chat_member(
                chat_id=channel.channel_id,
                user_id=user_id,
            )
            if member.status not in _SUBSCRIBED_STATUSES:
                not_subscribed.append(channel)

        except TelegramForbiddenError:
            # Bot kanaldan chiqarilgan yoki admin emas — kanalga obunani tekshira olmaymiz
            logger.warning(
                f"Subscription check failed (bot not admin): channel_id={channel.channel_id}"
            )
            not_subscribed.append(channel)

        except TelegramBadRequest as e:
            err = str(e).lower()
            if "user not found" in err or "chat not found" in err:
                # Foydalanuvchi yoki kanal topilmadi → obuna emas
                not_subscribed.append(channel)
            else:
                logger.warning(
                    f"Subscription check BadRequest: channel_id={channel.channel_id} err={e}"
                )
                not_subscribed.append(channel)

        except Exception as e:
            logger.warning(
                f"Subscription check unexpected error: channel_id={channel.channel_id} err={e}"
            )
            not_subscribed.append(channel)

    return not_subscribed


def _is_fake_channel_id(channel_id: int) -> bool:
    """
    Fake ID — join-request link'dan generatsiya qilingan
    (qarang: crud/channel.py _join_link_fake_id).
    Real Telegram kanal IDlari -100XXXXXXXXXX (13+ xona), fake IDlar -1 dan -99_999_999 gacha.
    """
    return -100_000_000 < channel_id < 0


async def check_bot_is_admin(bot: Bot, channel_id: int) -> bool:
    """Bot kanalda admin ekanligini tekshiradi"""
    try:
        bot_info = await bot.get_me()
        member = await bot.get_chat_member(chat_id=channel_id, user_id=bot_info.id)
        return member.status in ("administrator", "creator")
    except Exception:
        return False

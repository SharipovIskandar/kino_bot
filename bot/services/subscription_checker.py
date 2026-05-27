from typing import List

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest

from bot.database.models import MandatoryChannel


async def check_user_subscriptions(
    bot: Bot,
    user_id: int,
    channels: List[MandatoryChannel],
) -> List[MandatoryChannel]:
    """
    Foydalanuvchining har bir majburiy kanalga obuna bo'lgan-bo'lmaganligini tekshiradi.

    Returns: Obuna bo'lmagan kanallar ro'yxati (bo'sh ro'yxat = hammasi obuna)
    """
    not_subscribed = []

    for channel in channels:
        try:
            # channel_id butun son bo'lishi kerak, lekin ba'zan string kelishi mumkin
            c_id = int(channel.channel_id) if str(channel.channel_id).replace("-", "").isdigit() else channel.channel_id
            
            member = await bot.get_chat_member(
                chat_id=c_id,
                user_id=user_id,
            )
            # left yoki kicked bo'lsa obuna emas
            if member.status in ("left", "kicked"):
                not_subscribed.append(channel)
        except (TelegramForbiddenError, TelegramBadRequest) as e:
            # Bot kanalga kira olmayapti yoki user topilmadi — skip
            pass
        except Exception:
            # Boshqa kutilmagan xatolar — skip (xavfsizlik uchun)
            pass

    return not_subscribed


async def check_bot_is_admin(bot: Bot, channel_id: int) -> bool:
    """Bot kanalda admin ekanligini tekshiradi"""
    try:
        bot_info = await bot.get_me()
        member = await bot.get_chat_member(chat_id=channel_id, user_id=bot_info.id)
        return member.status in ("administrator", "creator")
    except Exception:
        return False

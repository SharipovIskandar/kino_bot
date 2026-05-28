from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import settings
from bot.database.crud.channel import get_active_channels
from bot.services.subscription_checker import check_user_subscriptions
from bot.keyboards.user_kb import build_subscription_keyboard
from bot.services.i18n import get_text

BYPASS_COMMANDS = {"/start", "/help"}
BYPASS_CALLBACKS = {"check_sub"}


async def _get_invite_links(bot, channels: list, session=None) -> dict:
    """
    Yopiq kanallar uchun invite link generatsiya qilish.
    Join request link'i (`t.me/+`) allaqachon saqlangan bo'lsa — ustiga yozmaydi.
    """
    urls = {}
    for ch in channels:
        # Allaqachon link bor (join request yoki oddiy) — ishlatamiz
        if ch.invite_link:
            urls[ch.channel_id] = ch.invite_link
            continue
        # Username bor — @username linkini yasaymiz
        if ch.channel_username:
            continue
        # Na link, na username — export qilamiz (faqat oddiy private kanallar uchun)
        try:
            link = await bot.export_chat_invite_link(ch.channel_id)
            urls[ch.channel_id] = link
            if session is not None:
                ch.invite_link = link
        except Exception:
            pass
    return urls


class SubscriptionMiddleware(BaseMiddleware):
    """
    Majburiy kanal obunasini tekshiradi.
    Adminlar va super adminlar bu middleware'dan o'tib ketadi.
    Redis orqali 60s ichida bir foydalanuvchiga faqat bitta xabar yuboriladi.
    """

    def __init__(self, redis: Redis) -> None:
        self.redis = redis

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        from aiogram.types import User as TgUser
        from bot.database.models import User as DbUser

        # Redis ni data orqali handlerlarga uzatish
        data["redis"] = self.redis

        tg_user: TgUser | None = data.get("event_from_user")
        db_user: DbUser | None = data.get("db_user")
        session: AsyncSession | None = data.get("session")
        lang: str = data.get("lang", "uz")
        bot = data.get("bot")

        if not tg_user or not session or not bot:
            return await handler(event, data)

        # Super admin va adminlar obunasiz ishlay oladi
        if tg_user.id in settings.super_admin_list:
            return await handler(event, data)

        if db_user and db_user.admin_profile is not None:
            return await handler(event, data)

        # Bypass buyruqlari
        if isinstance(event, Message) and event.text:
            cmd = event.text.split()[0] if event.text.startswith("/") else ""
            if cmd in BYPASS_COMMANDS:
                return await handler(event, data)

        # Bypass callbacklar
        if isinstance(event, CallbackQuery):
            if event.data and any(event.data.startswith(bp) for bp in BYPASS_CALLBACKS):
                return await handler(event, data)

        channels = await get_active_channels(session)
        if not channels:
            return await handler(event, data)

        not_subscribed = await check_user_subscriptions(
            bot=bot,
            user_id=tg_user.id,
            channels=channels,
        )

        if not not_subscribed:
            return await handler(event, data)

        # Har safar ogohlantirish ko'rsatiladi — ThrottlingMiddleware spam'ni boshqaradi
        text = get_text("subscription-required", lang)
        channel_urls = await _get_invite_links(bot, not_subscribed, session=session)
        keyboard = build_subscription_keyboard(not_subscribed, lang, channel_urls=channel_urls)

        if isinstance(event, Message):
            await event.answer(text, reply_markup=keyboard)
        elif isinstance(event, CallbackQuery):
            await event.message.answer(text, reply_markup=keyboard)
            await event.answer()

        return

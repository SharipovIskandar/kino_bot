from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import settings
from bot.database.crud.channel import get_active_channels
from bot.services.subscription_checker import check_user_subscriptions
from bot.keyboards.user_kb import build_subscription_keyboard
from bot.services.i18n import get_text

# Buyruqlar — obuna tekshiruvisiz o'tkaziladi
BYPASS_COMMANDS = {"/start", "/help", "/language"}
# Callbacklar — obuna tekshiruvisiz o'tkaziladi
BYPASS_CALLBACKS = {"check_sub", "lang_"}


class SubscriptionMiddleware(BaseMiddleware):
    """
    Majburiy kanal obunasini tekshiradi.
    Adminlar va super adminlar bu middleware'dan o'tib ketadi.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        from aiogram.types import User as TgUser
        from bot.database.models import User as DbUser

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

        # Bypass buyruqlari
        if isinstance(event, Message) and event.text:
            cmd = event.text.split()[0] if event.text.startswith("/") else ""
            if cmd in BYPASS_COMMANDS:
                return await handler(event, data)

        # Bypass callbacklar
        if isinstance(event, CallbackQuery):
            if event.data and any(event.data.startswith(bp) for bp in BYPASS_CALLBACKS):
                return await handler(event, data)

        # Aktiv kanallar ro'yxatini olish
        channels = await get_active_channels(session)
        if not channels:
            # Majburiy kanal yo'q — o'tkazib yuboramiz
            return await handler(event, data)

        # Obunani tekshirish
        not_subscribed = await check_user_subscriptions(
            bot=bot,
            user_id=tg_user.id,
            channels=channels,
        )

        if not not_subscribed:
            # Hammasiga obuna bo'lgan
            return await handler(event, data)

        # Obuna bo'lmagan kanallar bor — xabar yuboramiz
        text = get_text("subscription-required", lang)
        keyboard = build_subscription_keyboard(not_subscribed, lang)

        if isinstance(event, Message):
            await event.answer(text, reply_markup=keyboard)
        elif isinstance(event, CallbackQuery):
            await event.message.answer(text, reply_markup=keyboard)
            await event.answer()

        return  # handler'ga yo'l bermaymiz

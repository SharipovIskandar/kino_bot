from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery

from bot.database.models import User
from bot.services.i18n import get_text


class BanCheckMiddleware(BaseMiddleware):
    """
    Banlangan foydalanuvchilarni bloklaydi.
    Admin va super adminlarga tegmaydi.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        db_user: User | None = data.get("db_user")
        lang: str = data.get("lang", "uz")

        if db_user and db_user.is_banned:
            text = get_text(
                "error-banned",
                lang,
                reason=db_user.ban_reason or "",
            )
            if isinstance(event, Message):
                await event.answer(text)
            elif isinstance(event, CallbackQuery):
                await event.answer(text, show_alert=True)
            return  # handler'ga yo'l bermaymiz

        return await handler(event, data)

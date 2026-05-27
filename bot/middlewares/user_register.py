from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User as TgUser
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.crud.user import get_or_create_user, update_last_active
from bot.config import settings


class UserRegisterMiddleware(BaseMiddleware):
    """
    Har yangi update'da foydalanuvchini DB'da ro'yxatdan o'tkazadi.
    Mavjud bo'lsa last_active_at yangilaydi.
    User objectini data'ga qo'shadi.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        tg_user: TgUser | None = data.get("event_from_user")
        session: AsyncSession | None = data.get("session")

        if tg_user and session and not tg_user.is_bot:
            user, created = await get_or_create_user(
                session=session,
                telegram_id=tg_user.id,
                full_name=tg_user.full_name,
                username=tg_user.username,
                language=(tg_user.language_code or settings.default_language).lower(),
            )
            data["db_user"] = user
            data["lang"] = user.language.value

        return await handler(event, data)

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery


class BotFilterMiddleware(BaseMiddleware):
    """
    Bot tomonidan yuborilgan xabarlarni va private bo'lmagan
    chatlardan kelgan eventlarni to'liq o'tkazib yuboradi.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        from aiogram.types import User as TgUser

        tg_user: TgUser | None = data.get("event_from_user")

        # Bot yoki anonim sender bo'lsa — e'tiborsiz qoldiramiz
        if tg_user and tg_user.is_bot:
            return

        # Message faqat private chatda ishlaydi
        if isinstance(event, Message):
            if event.chat.type != "private":
                return

        # CallbackQuery ham faqat private chatda
        if isinstance(event, CallbackQuery):
            if event.message and event.message.chat.type != "private":
                return

        return await handler(event, data)

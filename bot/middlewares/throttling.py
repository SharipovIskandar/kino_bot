from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from redis.asyncio import Redis

from bot.config import settings


class ThrottlingMiddleware(BaseMiddleware):
    """
    Spam himoya — Redis orqali rate limiter.
    1 daqiqada THROTTLE_RATE dan ko'p so'rov yuborsa blok qilinadi.
    """

    def __init__(self, redis: Redis, rate: int | None = None):
        self.redis = redis
        self.rate = rate or settings.throttle_rate

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        from aiogram.types import User as TgUser
        tg_user: TgUser | None = data.get("event_from_user")

        if not tg_user or tg_user.is_bot:
            return await handler(event, data)

        key = f"throttle:{tg_user.id}"
        count = await self.redis.incr(key)

        if count == 1:
            # Birinchi so'rov — 60 soniyalik timer boshlaydi
            await self.redis.expire(key, 60)

        if count > self.rate:
            # Limit oshdi — xabar yubormay o'tamiz
            if isinstance(event, CallbackQuery):
                await event.answer("⏳ Iltimos, biroz kuting...", show_alert=False)
            # Message bo'lsa javob bermaymiz (spam bo'lmasligi uchun)
            return

        return await handler(event, data)

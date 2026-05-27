import asyncio
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from loguru import logger
from redis.asyncio import Redis

from bot.config import settings
from bot.database.connection import close_db

# ── Middlewares ───────────────────────────────────────────────────────────────
from bot.middlewares.database import DatabaseMiddleware
from bot.middlewares.user_register import UserRegisterMiddleware
from bot.middlewares.ban_check import BanCheckMiddleware
from bot.middlewares.throttling import ThrottlingMiddleware

# ── Handlers ──────────────────────────────────────────────────────────────────
from bot.handlers.user.start import router as start_router
from bot.handlers.user.search import router as search_router
from bot.handlers.user.subscription import router as subscription_router
from bot.handlers.channel_post import router as channel_post_router
from bot.handlers.admin.panel import router as admin_panel_router
from bot.handlers.admin.channels import router as admin_channels_router
from bot.handlers.admin.stats import router as admin_stats_router
from bot.handlers.admin.admins import router as admin_admins_router
from bot.handlers.admin.broadcast import router as admin_broadcast_router
from bot.handlers.admin.moderation import router as admin_moderation_router
from bot.handlers.admin.movies import router as admin_movies_router


def setup_logging() -> None:
    """Loguru konfiguratsiyasi"""
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO",
    )
    logger.add(
        "logs/kinobot.log",
        rotation="10 MB",
        retention="7 days",
        compression="zip",
        level="DEBUG",
    )


async def main() -> None:
    setup_logging()
    logger.info("KinoBot ishga tushmoqda...")

    # ── Redis ─────────────────────────────────────────────────────────────────
    redis = Redis.from_url(settings.redis_url, decode_responses=False)
    storage = RedisStorage(redis=redis)

    # ── Bot va Dispatcher ────────────────────────────────────────────────────
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=storage)

    # ── Middlewares (tartib muhim!) ───────────────────────────────────────────
    dp.message.middleware(DatabaseMiddleware())
    dp.callback_query.middleware(DatabaseMiddleware())

    dp.message.middleware(UserRegisterMiddleware())
    dp.callback_query.middleware(UserRegisterMiddleware())

    dp.message.middleware(BanCheckMiddleware())
    dp.callback_query.middleware(BanCheckMiddleware())

    dp.message.middleware(ThrottlingMiddleware(redis=redis))

    # channel_post uchun faqat DB session kerak (user yo'q)
    dp.channel_post.middleware(DatabaseMiddleware())

    # ── Routerlar ──────────────────────────────────────────────────────────────
    dp.include_router(channel_post_router)
    dp.include_router(start_router)
    dp.include_router(subscription_router)
    dp.include_router(search_router)
    dp.include_router(admin_panel_router)
    dp.include_router(admin_channels_router)
    dp.include_router(admin_stats_router)
    dp.include_router(admin_admins_router)
    dp.include_router(admin_broadcast_router)
    dp.include_router(admin_moderation_router)
    dp.include_router(admin_movies_router)

    # ── Global Error Handler ─────────────────────────────────────────────────
    from aiogram.types import ErrorEvent
    @dp.error()
    async def global_error_handler(event: ErrorEvent):
        logger.exception(f"Kutilmagan xato: {event.exception}")
        # Super adminlarga xabar berish
        for admin_id in settings.super_admin_list:
            try:
                await event.bot.send_message(
                    admin_id,
                    f"❌ <b>Kutilmagan xato yuz berdi!</b>\n\n"
                    f"💬 Xabar: <code>{str(event.exception)[:1000]}</code>\n"
                    f"ℹ️ Update ID: <code>{event.update.update_id}</code>"
                )
            except Exception:
                pass

    # ── Bot commandlarini Telegram'ga ro'yxatdan o'tkazish ───────────────────
    from aiogram.types import BotCommand, BotCommandScopeDefault, BotCommandScopeChat

    # Barcha userlarga — faqat asosiy buyruqlar
    user_commands = [
        BotCommand(command="start",    description="Botni boshlash"),
        BotCommand(command="search",   description="Kino qidirish"),
        BotCommand(command="language", description="Tilni o'zgartirish"),
        BotCommand(command="help",     description="Yordam"),
    ]
    await bot.set_my_commands(user_commands, scope=BotCommandScopeDefault())

    # Super adminlarga — to'liq buyruqlar ro'yxati
    admin_commands = user_commands + [
        BotCommand(command="admin",    description="Admin panel"),
        BotCommand(command="ban",      description="Userni ban qilish"),
        BotCommand(command="unban",    description="Unban qilish"),
        BotCommand(command="userinfo", description="User ma'lumoti"),
    ]
    for admin_id in settings.super_admin_list:
        try:
            await bot.set_my_commands(
                admin_commands,
                scope=BotCommandScopeChat(chat_id=admin_id)
            )
        except Exception:
            pass  # Admin hali botni boshlamaganligi bo'lishi mumkin

    logger.info("Bot muvaffaqiyatli ishga tushdi!")

    try:
        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types(),
        )
    finally:
        logger.info("Bot to'xtatilmoqda...")
        await bot.session.close()
        await close_db()
        await redis.aclose()


if __name__ == "__main__":
    asyncio.run(main())

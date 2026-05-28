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
from bot.middlewares.bot_filter import BotFilterMiddleware
from bot.middlewares.database import DatabaseMiddleware
from bot.middlewares.user_register import UserRegisterMiddleware
from bot.middlewares.ban_check import BanCheckMiddleware
from bot.middlewares.subscription import SubscriptionMiddleware
from bot.middlewares.throttling import ThrottlingMiddleware

# ── Handlers ──────────────────────────────────────────────────────────────────
from bot.handlers.user.start import router as start_router
from bot.handlers.user.search import router as search_router
from bot.handlers.user.subscription import router as subscription_router
from bot.handlers.user.fallback import router as fallback_router
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


async def run_admin_server() -> None:
    import uvicorn
    from admin.main import app as admin_app
    config = uvicorn.Config(
        app=admin_app,
        host="0.0.0.0",
        port=settings.admin_port,
        log_level="warning",
    )
    server = uvicorn.Server(config=config)
    # Signal handlerlarni o'chiramiz — dp.start_polling() o'zi boshqaradi
    server.install_signal_handlers = lambda: None
    logger.info(f"Admin panel http://0.0.0.0:{settings.admin_port} portida ishga tushmoqda...")
    await server.serve()


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
    # BotFilter birinchi — bot va group eventlarni darhol to'xtatadi
    dp.message.middleware(BotFilterMiddleware())
    dp.callback_query.middleware(BotFilterMiddleware())

    dp.message.middleware(DatabaseMiddleware())
    dp.callback_query.middleware(DatabaseMiddleware())

    dp.message.middleware(UserRegisterMiddleware())
    dp.callback_query.middleware(UserRegisterMiddleware())

    dp.message.middleware(BanCheckMiddleware())
    dp.callback_query.middleware(BanCheckMiddleware())

    dp.message.middleware(SubscriptionMiddleware(redis=redis))
    dp.callback_query.middleware(SubscriptionMiddleware(redis=redis))

    dp.message.middleware(ThrottlingMiddleware(redis=redis))
    dp.callback_query.middleware(ThrottlingMiddleware(redis=redis))

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
    # fallback eng oxirida — boshqa hech narsa uslambagan xabarlar uchun
    dp.include_router(fallback_router)

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

    # Barcha userlarga — asosiy buyruqlar
    user_commands = [
        BotCommand(command="start",  description="Botni boshlash"),
        BotCommand(command="search", description="Kino qidirish"),
        BotCommand(command="cancel", description="Amalni bekor qilish"),
        BotCommand(command="help",   description="Yordam"),
    ]
    await bot.set_my_commands(user_commands, scope=BotCommandScopeDefault())

    # Bot tavsifi — /start bosilmasdan oldin ko'rinadigan matn
    bot_description = (
        "🎬 KinoBot — O'zbek kinolar boti\n\n"
        "Bu bot orqali minglab kinolarni bepul tomosha qilishingiz mumkin!\n\n"
        "📌 Foydalanish:\n"
        "• Kino kodini yuboring → kino darhol keladi\n"
        "• /search — kino nomini qidirish\n\n"
        "▶️ Boshlash uchun Start tugmasini bosing!"
    )
    bot_short_description = "🎬 Kino kodini yuboring — kino darhol keladi!"

    try:
        await bot.set_my_description(bot_description)
        await bot.set_my_short_description(bot_short_description)
    except Exception:
        pass  # Eski Telegram versiyalarida bu API bo'lmasligi mumkin

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

    coroutines = [dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())]
    if settings.run_admin:
        coroutines.append(run_admin_server())

    try:
        await asyncio.gather(*coroutines)
    finally:
        logger.info("Bot to'xtatilmoqda...")
        await bot.session.close()
        await close_db()
        await redis.aclose()


if __name__ == "__main__":
    asyncio.run(main())

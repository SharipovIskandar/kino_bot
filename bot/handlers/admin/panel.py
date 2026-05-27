import asyncio
import time
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import settings
from bot.database.models import User
from bot.keyboards.admin_kb import (
    build_admin_panel_keyboard,
    build_back_to_panel_keyboard,
)
from bot.services.i18n import get_text
from bot.services.movie_sync import sync_movies_from_channel

router = Router(name="admin_panel")

# Sync mutex — bir anda bir sync
_sync_running = False


def is_admin(user_id: int, db_user: User | None) -> bool:
    """Admin ekanligini tekshirish"""
    if user_id in settings.super_admin_list:
        return True
    if db_user and db_user.admin_profile:
        return True
    return False


@router.message(Command("admin"))
async def cmd_admin(
    message: Message,
    db_user: User,
    lang: str,
) -> None:
    """Admin panel buyrug'i"""
    if not is_admin(message.from_user.id, db_user):
        await message.answer(get_text("access-denied", lang))
        return

    role = "Super Admin" if message.from_user.id in settings.super_admin_list else "Admin"
    await message.answer(
        get_text("admin-panel", lang, name=message.from_user.full_name, role=role),
        reply_markup=build_admin_panel_keyboard(lang),
    )


@router.callback_query(F.data == "admin:panel")
async def callback_admin_panel(
    callback: CallbackQuery,
    db_user: User,
    lang: str,
) -> None:
    """Admin panelga qaytish"""
    if not is_admin(callback.from_user.id, db_user):
        await callback.answer(get_text("access-denied", lang), show_alert=True)
        return

    role = "Super Admin" if callback.from_user.id in settings.super_admin_list else "Admin"
    await callback.message.edit_text(
        get_text("admin-panel", lang, name=callback.from_user.full_name, role=role),
        reply_markup=build_admin_panel_keyboard(lang),
    )
    await callback.answer()


@router.callback_query(F.data == "admin:sync")
async def callback_sync(
    callback: CallbackQuery,
    session: AsyncSession,
    db_user: User,
    lang: str,
    bot,
) -> None:
    """Kino sync boshlash"""
    global _sync_running

    if not is_admin(callback.from_user.id, db_user):
        await callback.answer(get_text("access-denied", lang), show_alert=True)
        return

    if _sync_running:
        await callback.answer(get_text("sync-already-running", lang), show_alert=True)
        return

    _sync_running = True
    await callback.message.edit_text(get_text("sync-started", lang))
    await callback.answer()

    start_time = time.time()
    try:
        sync_log = await sync_movies_from_channel(
            bot=bot,
            session=session,
            triggered_by=callback.from_user.id,
        )

        duration = round(time.time() - start_time, 1)

        if sync_log.status.value == "done":
            text = get_text(
                "sync-done", lang,
                added=sync_log.movies_added,
                updated=sync_log.movies_updated,
                skipped=sync_log.movies_skipped,
                duration=duration,
            )
        else:
            text = get_text("sync-failed", lang, error=sync_log.error_message or "")

    except Exception as e:
        text = get_text("sync-failed", lang, error=str(e))
    finally:
        _sync_running = False

    await callback.message.edit_text(
        text,
        reply_markup=build_back_to_panel_keyboard(lang),
    )

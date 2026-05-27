from aiogram import Router, F
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.crud.movie import get_movies_paginated, delete_movie
from bot.database.models import User
from bot.handlers.admin.panel import is_admin
from bot.keyboards.admin_kb import build_admin_panel_keyboard, build_back_to_panel_keyboard
from bot.services.i18n import get_text
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

router = Router(name="admin_movies")

MOVIES_PER_PAGE = 10

@router.callback_query(F.data == "admin:movies")
@router.callback_query(F.data.startswith("admin:movies:p:"))
async def callback_admin_movies(
    callback: CallbackQuery,
    session: AsyncSession,
    db_user: User,
    lang: str,
) -> None:
    """Admin uchun kinolar ro'yxati"""
    if not is_admin(callback.from_user.id, db_user):
        await callback.answer(get_text("access-denied", lang), show_alert=True)
        return

    # Callback data'dan offset'ni olish
    parts = callback.data.split(":")
    offset = int(parts[3]) if len(parts) > 3 else 0

    movies, total = await get_movies_paginated(session, limit=MOVIES_PER_PAGE, offset=offset)

    if not movies:
        await callback.message.edit_text(
            "🎬 Kinolar topilmadi.",
            reply_markup=build_back_to_panel_keyboard(lang)
        )
        return

    text = f"🎬 <b>Kinolar ro'yxati</b> ({total} ta):\n\n"
    for i, movie in enumerate(movies, start=offset + 1):
        text += f"{i}. <code>{movie.code}</code> — {movie.get_title(lang)[:30]}\n"

    # Klaviatura yaratish
    builder = InlineKeyboardBuilder()
    
    # Har bir kino uchun o'chirish tugmasi (misol uchun)
    for movie in movies:
        builder.row(
            InlineKeyboardButton(
                text=f"🗑 {movie.code}",
                callback_data=f"admin:movie:rm:{movie.code}:{offset}"
            )
        )

    # Navigatsiya
    nav_row = []
    if offset > 0:
        nav_row.append(InlineKeyboardButton(text="◀️", callback_data=f"admin:movies:p:{max(0, offset - MOVIES_PER_PAGE)}"))
    if offset + MOVIES_PER_PAGE < total:
        nav_row.append(InlineKeyboardButton(text="▶️", callback_data=f"admin:movies:p:{offset + MOVIES_PER_PAGE}"))
    
    if nav_row:
        builder.row(*nav_row)

    builder.row(InlineKeyboardButton(text=get_text("btn-back", lang), callback_data="admin:panel"))

    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(F.data.startswith("admin:movie:rm:"))
async def callback_admin_movie_remove(
    callback: CallbackQuery,
    session: AsyncSession,
    db_user: User,
    lang: str,
) -> None:
    """Kinoni o'chirish"""
    if not is_admin(callback.from_user.id, db_user):
        await callback.answer(get_text("access-denied", lang), show_alert=True)
        return

    parts = callback.data.split(":")
    code = parts[3]
    offset = parts[4] if len(parts) > 4 else 0

    success = await delete_movie(session, code)
    if success:
        await callback.answer(f"✅ {code} o'chirildi", show_alert=True)
    else:
        await callback.answer(f"❌ Xatolik", show_alert=True)

    # Ro'yxatni yangilash
    await callback.message.edit_text("🔄 Yangilanmoqda...")
    # Fake callback data create
    callback.data = f"admin:movies:p:{offset}"
    await callback_admin_movies(callback, session, db_user, lang)

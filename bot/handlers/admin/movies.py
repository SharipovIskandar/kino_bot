from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from bot.database.crud.movie import get_movies_paginated, delete_movie
from bot.database.models import User, Movie, MovieLanguageType
from bot.handlers.admin.panel import is_admin
from bot.keyboards.admin_kb import build_back_to_panel_keyboard
from bot.services.i18n import get_text

router = Router(name="admin_movies")
MOVIES_PER_PAGE = 10


class MovieEditState(StatesGroup):
    edit_title = State()
    edit_description = State()
    edit_meta = State()
    edit_message_id = State()


# ── Helpers ────────────────────────────────────────────────────────────────────

def _movie_info_text(movie: Movie) -> str:
    lines = [f"🎬 <b>{movie.code}</b>  {'🟢 Faol' if movie.is_active else '🔴 Nofaol'}\n"]
    lines.append(f"📛 Nom: {movie.title or '—'}\n")
    lines.append(f"📅 Yil: {movie.year or '—'}   ⏱ {(str(movie.duration) + ' min') if movie.duration else '—'}")
    lines.append(f"🌍 {movie.country or '—'}   🔞 {movie.age_rating or '—'}")
    lines.append(f"🎬 {movie.director or '—'}")
    if movie.cast:
        lines.append(f"👥 {movie.cast[:80]}")
    lines.append(f"⭐ IMDb: {movie.imdb_rating or '—'}   KP: {movie.kinopoisk_rating or '—'}")
    lines.append(f"🔊 {movie.language_type.value if movie.language_type else '—'}")
    lines.append(f"📨 MSG ID: <code>{movie.channel_message_id}</code>")
    lines.append(f"👁 Ko'rishlar: {movie.view_count}")
    return "\n".join(lines)


def _movie_edit_keyboard(code: str, is_active: bool, offset: int = 0) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✏️ Nom", callback_data=f"me:t:{code}"),
        InlineKeyboardButton(text="📝 Tavsif", callback_data=f"me:d:{code}"),
    )
    builder.row(
        InlineKeyboardButton(text="📊 Meta", callback_data=f"me:m:{code}"),
        InlineKeyboardButton(text="🔗 MSG ID", callback_data=f"me:i:{code}"),
    )
    toggle_text = "🔴 Nofaol qilish" if is_active else "🟢 Faollashtirish"
    builder.row(
        InlineKeyboardButton(text=toggle_text, callback_data=f"me:tg:{code}:{offset}"),
        InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"me:dl:{code}:{offset}"),
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Ro'yxat", callback_data=f"admin:movies:p:{offset}")
    )
    return builder.as_markup()


async def _get_movie(session: AsyncSession, code: str) -> Movie | None:
    result = await session.execute(
        select(Movie).where(Movie.code == code.upper().strip()).options(selectinload(Movie.genres))
    )
    return result.scalar_one_or_none()


# ── Movie list ─────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin:movies")
@router.callback_query(F.data.startswith("admin:movies:p:"))
async def callback_admin_movies(
    callback: CallbackQuery,
    session: AsyncSession,
    db_user: User,
    lang: str,
) -> None:
    if not is_admin(callback.from_user.id, db_user):
        await callback.answer(get_text("access-denied", lang), show_alert=True)
        return

    parts = callback.data.split(":")
    offset = int(parts[3]) if len(parts) > 3 else 0
    movies, total = await get_movies_paginated(session, limit=MOVIES_PER_PAGE, offset=offset, only_active=False)

    if not movies:
        await callback.message.edit_text("🎬 Kinolar topilmadi.", reply_markup=build_back_to_panel_keyboard(lang))
        await callback.answer()
        return

    text = f"🎬 <b>Kinolar ro'yxati</b> ({total} ta):\n\nKino tanlang:"

    builder = InlineKeyboardBuilder()
    for movie in movies:
        status = "🟢" if movie.is_active else "🔴"
        title = (movie.title or movie.code)[:22]
        builder.row(
            InlineKeyboardButton(
                text=f"{status} {movie.code} — {title}",
                callback_data=f"me:show:{movie.code}:{offset}"
            )
        )

    nav_row = []
    if offset > 0:
        nav_row.append(InlineKeyboardButton(text="◀️", callback_data=f"admin:movies:p:{max(0, offset - MOVIES_PER_PAGE)}"))
    if offset + MOVIES_PER_PAGE < total:
        nav_row.append(InlineKeyboardButton(text="▶️", callback_data=f"admin:movies:p:{offset + MOVIES_PER_PAGE}"))
    if nav_row:
        builder.row(*nav_row)
    builder.row(InlineKeyboardButton(text="◀️ Ortga", callback_data="admin:panel"))

    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()


# ── Movie detail ───────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("me:show:"))
async def callback_movie_show(
    callback: CallbackQuery,
    session: AsyncSession,
    db_user: User,
    lang: str,
) -> None:
    if not is_admin(callback.from_user.id, db_user):
        await callback.answer(get_text("access-denied", lang), show_alert=True)
        return

    parts = callback.data.split(":")
    code = parts[2]
    offset = int(parts[3]) if len(parts) > 3 else 0

    movie = await _get_movie(session, code)
    if not movie:
        await callback.answer("❌ Kino topilmadi", show_alert=True)
        return

    await callback.message.edit_text(
        _movie_info_text(movie),
        reply_markup=_movie_edit_keyboard(code, movie.is_active, offset)
    )
    await callback.answer()


# ── Toggle active ──────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("me:tg:"))
async def callback_movie_toggle(
    callback: CallbackQuery,
    session: AsyncSession,
    db_user: User,
    lang: str,
) -> None:
    if not is_admin(callback.from_user.id, db_user):
        await callback.answer(get_text("access-denied", lang), show_alert=True)
        return

    parts = callback.data.split(":")
    code = parts[2]
    offset = int(parts[3]) if len(parts) > 3 else 0

    movie = await _get_movie(session, code)
    if not movie:
        await callback.answer("❌ Kino topilmadi", show_alert=True)
        return

    movie.is_active = not movie.is_active
    status = "faollashtirildi" if movie.is_active else "nofaol qilindi"
    await callback.message.edit_text(
        _movie_info_text(movie),
        reply_markup=_movie_edit_keyboard(code, movie.is_active, offset)
    )
    await callback.answer(f"✅ {code} {status}")


# ── Delete ─────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("me:dl:"))
async def callback_movie_delete(
    callback: CallbackQuery,
    session: AsyncSession,
    db_user: User,
    lang: str,
) -> None:
    if not is_admin(callback.from_user.id, db_user):
        await callback.answer(get_text("access-denied", lang), show_alert=True)
        return

    parts = callback.data.split(":")
    code = parts[2]
    offset = int(parts[3]) if len(parts) > 3 else 0

    success = await delete_movie(session, code)
    if success:
        await callback.answer(f"✅ {code} o'chirildi", show_alert=True)
        callback.data = f"admin:movies:p:{offset}"
        await callback_admin_movies(callback, session, db_user, lang)
    else:
        await callback.answer("❌ Xatolik", show_alert=True)


# ── Edit title ─────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("me:t:"))
async def callback_edit_title(
    callback: CallbackQuery,
    session: AsyncSession,
    db_user: User,
    lang: str,
    state: FSMContext,
) -> None:
    if not is_admin(callback.from_user.id, db_user):
        await callback.answer(get_text("access-denied", lang), show_alert=True)
        return

    code = callback.data.split(":")[2]
    movie = await _get_movie(session, code)
    if not movie:
        await callback.answer("❌ Kino topilmadi", show_alert=True)
        return

    await state.set_state(MovieEditState.edit_title)
    await state.update_data(edit_code=code)

    await callback.message.answer(
        f"✏️ <b>{code}</b> nomini tahrirlang.\n\n"
        f"Hozirgi: {movie.title or '—'}\n\n"
        f"Yangi nomni yuboring:"
    )
    await callback.answer()


@router.message(MovieEditState.edit_title)
async def process_edit_title(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    data = await state.get_data()
    code = data.get("edit_code")
    await state.clear()

    movie = await _get_movie(session, code)
    if not movie:
        await message.answer("❌ Kino topilmadi")
        return

    new_title = message.text.strip()
    if new_title and new_title != "-":
        movie.title = new_title

    await message.answer(
        f"✅ Nom yangilandi.\n\n" + _movie_info_text(movie),
        reply_markup=_movie_edit_keyboard(code, movie.is_active)
    )


# ── Edit description ───────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("me:d:"))
async def callback_edit_description(
    callback: CallbackQuery,
    session: AsyncSession,
    db_user: User,
    lang: str,
    state: FSMContext,
) -> None:
    if not is_admin(callback.from_user.id, db_user):
        await callback.answer(get_text("access-denied", lang), show_alert=True)
        return

    code = callback.data.split(":")[2]
    movie = await _get_movie(session, code)
    if not movie:
        await callback.answer("❌ Kino topilmadi", show_alert=True)
        return

    await state.set_state(MovieEditState.edit_description)
    await state.update_data(edit_code=code)

    await callback.message.answer(
        f"📝 <b>{code}</b> tavsifini tahrirlang.\n\n"
        f"Yangi tavsifni yuboring:"
    )
    await callback.answer()


@router.message(MovieEditState.edit_description)
async def process_edit_description(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    data = await state.get_data()
    code = data.get("edit_code")
    await state.clear()

    movie = await _get_movie(session, code)
    if not movie:
        await message.answer("❌ Kino topilmadi")
        return

    val = message.text.strip()
    if val and val != "-":
        movie.description = val

    await message.answer(
        f"✅ Tavsif yangilandi.",
        reply_markup=_movie_edit_keyboard(code, movie.is_active)
    )


# ── Edit metadata ──────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("me:m:"))
async def callback_edit_meta(
    callback: CallbackQuery,
    session: AsyncSession,
    db_user: User,
    lang: str,
    state: FSMContext,
) -> None:
    if not is_admin(callback.from_user.id, db_user):
        await callback.answer(get_text("access-denied", lang), show_alert=True)
        return

    code = callback.data.split(":")[2]
    movie = await _get_movie(session, code)
    if not movie:
        await callback.answer("❌ Kino topilmadi", show_alert=True)
        return

    await state.set_state(MovieEditState.edit_meta)
    await state.update_data(edit_code=code)

    lang_types = " | ".join(lt.value for lt in MovieLanguageType)

    await callback.message.answer(
        f"📊 <b>{code}</b> metadata.\n\n"
        f"Hozirgi:\n"
        f"yil: {movie.year or '—'}\n"
        f"davom: {movie.duration or '—'}\n"
        f"mamlakat: {movie.country or '—'}\n"
        f"rejissyor: {movie.director or '—'}\n"
        f"aktyor: {movie.cast or '—'}\n"
        f"imdb: {movie.imdb_rating or '—'}\n"
        f"kino: {movie.kinopoisk_rating or '—'}\n"
        f"yosh: {movie.age_rating or '—'}\n"
        f"til: {movie.language_type.value if movie.language_type else '—'}\n\n"
        f"O'zgartirmoqchi bo'lganlaringizni yuboring:\n"
        f"<code>yil: 2010\ndavom: 148\nmamlakat: AQSh\nrejissyor: Nolan\n"
        f"aktyor: DiCaprio, Hardy\nimdb: 8.8\nkino: 8.6\nyosh: 16+\ntil: dubbed_uz</code>\n\n"
        f"Til turlari: <code>{lang_types}</code>"
    )
    await callback.answer()


@router.message(MovieEditState.edit_meta)
async def process_edit_meta(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    data = await state.get_data()
    code = data.get("edit_code")
    await state.clear()

    movie = await _get_movie(session, code)
    if not movie:
        await message.answer("❌ Kino topilmadi")
        return

    for line in message.text.strip().split("\n"):
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip().lower()
        val = val.strip()
        if not val or val == "-":
            continue
        try:
            if key == "yil":
                movie.year = int(val)
            elif key == "davom":
                movie.duration = int(val)
            elif key == "mamlakat":
                movie.country = val
            elif key == "rejissyor":
                movie.director = val
            elif key == "aktyor":
                movie.cast = val
            elif key == "imdb":
                movie.imdb_rating = float(val)
            elif key == "kino":
                movie.kinopoisk_rating = float(val)
            elif key == "yosh":
                movie.age_rating = val
            elif key == "til":
                movie.language_type = MovieLanguageType(val)
        except (ValueError, Exception):
            pass  # Noto'g'ri qiymat — o'tkazib yuboramiz

    await message.answer(
        f"✅ Meta yangilandi.\n\n" + _movie_info_text(movie),
        reply_markup=_movie_edit_keyboard(code, movie.is_active)
    )


# ── Edit message ID ────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("me:i:"))
async def callback_edit_message_id(
    callback: CallbackQuery,
    session: AsyncSession,
    db_user: User,
    lang: str,
    state: FSMContext,
) -> None:
    if not is_admin(callback.from_user.id, db_user):
        await callback.answer(get_text("access-denied", lang), show_alert=True)
        return

    code = callback.data.split(":")[2]
    movie = await _get_movie(session, code)
    if not movie:
        await callback.answer("❌ Kino topilmadi", show_alert=True)
        return

    await state.set_state(MovieEditState.edit_message_id)
    await state.update_data(edit_code=code)

    await callback.message.answer(
        f"🔗 <b>{code}</b> kanal xabar ID sini yangilang.\n\n"
        f"Hozirgi: <code>{movie.channel_message_id}</code>\n\n"
        f"Yangi raqamni yuboring:"
    )
    await callback.answer()


@router.message(MovieEditState.edit_message_id)
async def process_edit_message_id(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    data = await state.get_data()
    code = data.get("edit_code")
    await state.clear()

    try:
        new_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Faqat raqam kiriting.")
        return

    movie = await _get_movie(session, code)
    if not movie:
        await message.answer("❌ Kino topilmadi")
        return

    movie.channel_message_id = new_id
    await message.answer(
        f"✅ MSG ID <code>{new_id}</code> ga yangilandi.",
        reply_markup=_movie_edit_keyboard(code, movie.is_active)
    )

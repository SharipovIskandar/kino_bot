from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.crud.movie import (
    get_movie_by_code, search_movies, record_view,
    get_random_movie, get_popular_movies,
)
from bot.database.models import User, Movie
from bot.keyboards.user_kb import build_main_menu, build_cancel_keyboard
from bot.services.i18n import get_text
from bot.config import settings


router = Router(name="search")

MOVIES_PER_PAGE = 5

_SEARCH_BTN = {"🔍 Qidirish"}
_RANDOM_BTN = {"🎲 Tasodifiy"}
_POPULAR_BTN = {"🔥 Mashhur"}
_CANCEL_TEXT = "❌ Bekor qilish"


class SearchState(StatesGroup):
    waiting_query = State()


# ── Qidiruv boshlash ──────────────────────────────────────────────────────────

@router.message(Command("search"))
@router.message(F.text.in_(_SEARCH_BTN))
async def cmd_search(
    message: Message,
    state: FSMContext,
    lang: str,
) -> None:
    await message.answer(
        get_text("search-prompt", lang),
        reply_markup=build_cancel_keyboard(lang),
    )
    await state.set_state(SearchState.waiting_query)


@router.message(SearchState.waiting_query)
async def process_search_query(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    lang: str,
) -> None:
    query = message.text.strip() if message.text else ""

    if not query:
        await message.answer(
            get_text("search-prompt", lang),
            reply_markup=build_cancel_keyboard(lang),
        )
        return

    if query == _CANCEL_TEXT:
        await state.clear()
        await message.answer(
            get_text("search-cancelled", lang),
            reply_markup=build_main_menu(lang),
        )
        return

    await state.clear()
    await _do_search(message, session, query, lang, state=state)


# ── Kino kodi to'g'ridan-to'g'ri kiritilsa ───────────────────────────────────

@router.message(F.text.regexp(r"^\d+$"))
async def process_movie_code(
    message: Message,
    session: AsyncSession,
    db_user: User,
    lang: str,
    bot,
) -> None:
    code = message.text.strip().upper()
    movie = await get_movie_by_code(session, code)

    if not movie:
        await message.answer(get_text("movie-not-found", lang, code=code))
        return

    await _send_movie(message, bot, session, movie, db_user, lang)


# ── Tasodifiy kino ────────────────────────────────────────────────────────────

@router.message(F.text.in_(_RANDOM_BTN))
async def cmd_random_movie(
    message: Message,
    session: AsyncSession,
    db_user: User,
    lang: str,
    bot,
) -> None:
    movie = await get_random_movie(session)
    if not movie:
        await message.answer(get_text("no-movies-available", lang))
        return
    await _send_movie(message, bot, session, movie, db_user, lang)


# ── Mashhur kinolar ───────────────────────────────────────────────────────────

@router.message(F.text.in_(_POPULAR_BTN))
async def cmd_popular_movies(
    message: Message,
    session: AsyncSession,
    lang: str,
) -> None:
    movies = await get_popular_movies(session, limit=5)
    if not movies:
        await message.answer(get_text("no-movies-available", lang))
        return

    text = get_text("popular-movies-header", lang) + "\n\n"
    builder = InlineKeyboardBuilder()
    for i, movie in enumerate(movies, 1):
        year = f" ({movie.year})" if movie.year else ""
        text += f"{i}. <b>{movie.get_title(lang)}</b>{year} — 👁 {movie.view_count:,}\n"
        builder.row(InlineKeyboardButton(
            text=f"🎬 {movie.get_title(lang)[:40]}",
            callback_data=f"popular:{movie.code}",
        ))

    await message.answer(text, reply_markup=builder.as_markup())


@router.callback_query(lambda c: c.data and c.data.startswith("popular:"))
async def process_popular_movie_select(
    callback: CallbackQuery,
    session: AsyncSession,
    db_user: User,
    lang: str,
    bot,
) -> None:
    code = callback.data.split(":")[1].upper()
    movie = await get_movie_by_code(session, code)
    if not movie:
        await callback.answer(get_text("movie-not-found", lang, code=code), show_alert=True)
        return
    await _send_movie(callback.message, bot, session, movie, db_user, lang)
    await callback.answer()


# ── Qidiruv: natijalar va pagination ─────────────────────────────────────────

async def _do_search(
    message: Message,
    session: AsyncSession,
    query: str,
    lang: str,
    offset: int = 0,
    state: FSMContext | None = None,
    edit_message: Message | None = None,
) -> None:
    movies, total = await search_movies(session, query, limit=MOVIES_PER_PAGE, offset=offset)

    if not movies:
        no_results = get_text("search-no-results", lang, query=query)
        if edit_message:
            try:
                await edit_message.edit_text(no_results, reply_markup=None)
            except TelegramBadRequest:
                pass
        else:
            await message.answer(no_results)
        return

    text = get_text("search-results-header", lang, query=query) + "\n\n"
    for i, movie in enumerate(movies, start=offset + 1):
        year = movie.year or ""
        text += get_text(
            "search-result-item", lang,
            num=i, title=movie.get_title(lang), year=year, code=movie.code,
        ) + "\n"
    text += f"\n{get_text('search-select-prompt', lang)}"

    keyboard = _build_search_results_keyboard(movies, query, offset, total, lang)

    if state is not None:
        await state.update_data(last_query=query, last_offset=offset)

    if edit_message:
        try:
            await edit_message.edit_text(text, reply_markup=keyboard)
        except TelegramBadRequest:
            pass
    else:
        await message.answer(text, reply_markup=keyboard)


def _build_search_results_keyboard(
    movies: list,
    query: str,
    offset: int,
    total: int,
    lang: str,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    for movie in movies:
        builder.row(InlineKeyboardButton(
            text=f"🎬 {movie.get_title(lang)[:40]}",
            callback_data=f"movie:{movie.code}",
        ))

    nav_row = []
    if offset > 0:
        nav_row.append(InlineKeyboardButton(
            text="◀️", callback_data=f"p:{offset - MOVIES_PER_PAGE}:{query[:40]}",
        ))
    if offset + MOVIES_PER_PAGE < total:
        nav_row.append(InlineKeyboardButton(
            text="▶️", callback_data=f"p:{offset + MOVIES_PER_PAGE}:{query[:40]}",
        ))
    if nav_row:
        builder.row(*nav_row)

    return builder.as_markup()


@router.callback_query(lambda c: c.data and c.data.startswith("movie:"))
async def process_movie_select(
    callback: CallbackQuery,
    session: AsyncSession,
    db_user: User,
    lang: str,
    bot,
    state: FSMContext,
) -> None:
    code = callback.data.split(":")[1].upper().strip()
    movie = await get_movie_by_code(session, code)

    if not movie:
        await callback.answer(get_text("movie-not-found", lang, code=code), show_alert=True)
        return

    await _send_movie(callback.message, bot, session, movie, db_user, lang, back_button=True)
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("p:"))
async def process_search_pagination(
    callback: CallbackQuery,
    session: AsyncSession,
    lang: str,
    state: FSMContext,
) -> None:
    parts = callback.data.split(":", 2)
    offset = int(parts[1]) if len(parts) > 1 else 0
    query = parts[2] if len(parts) > 2 else ""

    await _do_search(
        callback.message, session, query, lang,
        offset=offset, state=state, edit_message=callback.message,
    )
    await callback.answer()


@router.callback_query(F.data == "back_to_search")
async def process_back_to_search(
    callback: CallbackQuery,
    session: AsyncSession,
    lang: str,
    state: FSMContext,
) -> None:
    data = await state.get_data()
    query = data.get("last_query", "")
    offset = data.get("last_offset", 0)

    if not query:
        await callback.answer(get_text("search-no-results", lang, query=""), show_alert=True)
        return

    await _do_search(callback.message, session, query, lang, offset=offset, state=state)
    await callback.answer()


# ── Kino kartasi va yuborish ──────────────────────────────────────────────────

def _build_movie_caption(movie: Movie, is_new_view: bool = True) -> str:
    lines = [f"🎬 <b>{movie.title or movie.code}</b>"]

    meta = []
    if movie.year:
        meta.append(f"📅 {movie.year}")
    if movie.country:
        meta.append(f"🌍 {movie.country}")
    if movie.duration:
        meta.append(f"⏱ {movie.duration} daq.")
    if meta:
        lines.append("  ".join(meta))

    if movie.genres:
        lines.append("🎭 " + ", ".join(g.name for g in movie.genres))

    if movie.director:
        lines.append(f"👤 {movie.director}")

    if movie.cast:
        lines.append(f"👥 {movie.cast[:80]}{'...' if len(movie.cast) > 80 else ''}")

    ratings = []
    if movie.imdb_rating:
        ratings.append(f"⭐ IMDb: <b>{movie.imdb_rating}</b>")
    if movie.kinopoisk_rating:
        ratings.append(f"🎯 KP: <b>{movie.kinopoisk_rating}</b>")
    if ratings:
        lines.append("  ".join(ratings))

    if movie.language_type:
        lang_str = movie.language_type.value if hasattr(movie.language_type, "value") else str(movie.language_type)
        lines.append(f"🔊 {lang_str}")

    if movie.age_rating:
        lines.append(f"🔞 {movie.age_rating}")

    if movie.description:
        desc = movie.description[:300] + ("..." if len(movie.description) > 300 else "")
        lines.append(f"\n📝 <i>{desc}</i>")

    view_count = movie.view_count + (1 if is_new_view else 0)
    lines.append(f"\n🆔 Kod: <code>{movie.code}</code>   👁 {view_count:,} ko'rilgan")

    return "\n".join(lines)


async def _send_movie(
    message: Message,
    bot,
    session: AsyncSession,
    movie: Movie,
    db_user: User,
    lang: str,
    back_button: bool = False,
) -> None:
    is_new_view = False
    if db_user:
        is_new_view = await record_view(session, movie.id, db_user.id)

    caption = _build_movie_caption(movie, is_new_view=is_new_view)

    reply_markup = None
    if back_button:
        reply_markup = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(
                text=get_text("btn-back-to-results", lang),
                callback_data="back_to_search",
            )
        ]])

    try:
        await bot.copy_message(
            chat_id=message.chat.id,
            from_chat_id=settings.movie_channel_id,
            message_id=movie.channel_message_id,
            caption=caption,
            parse_mode="HTML",
            protect_content=True,
            reply_markup=reply_markup,
        )
    except TelegramBadRequest as e:
        if "message to copy not found" in str(e).lower() or "message_id_invalid" in str(e).lower():
            movie.is_active = False
            logger.warning(f"Movie {movie.code} deactivated: channel msg {movie.channel_message_id} not found")
            await message.answer(get_text("movie-not-found", lang, code=movie.code))
        else:
            logger.error(f"copy_message failed for {movie.code}: {e}")
            await message.answer(get_text("error-general", lang))
        return
    except Exception as e:
        logger.error(f"Movie send error {movie.code}: {type(e).__name__}")
        await message.answer(get_text("error-general", lang))

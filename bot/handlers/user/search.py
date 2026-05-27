import aiohttp

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.crud.movie import get_movie_by_code, search_movies, record_view
from bot.database.crud.channel import get_active_channels
from bot.database.models import User, Movie
from bot.services.i18n import get_text
from bot.services.subscription_checker import check_user_subscriptions
from bot.keyboards.user_kb import build_subscription_keyboard
from bot.config import settings


router = Router(name="search")

MOVIES_PER_PAGE = 5

# Reply keyboard matni — 3 tilda
_SEARCH_BTN = {"🔍 Qidirish", "🔍 Поиск", "🔍 Search"}


class SearchState(StatesGroup):
    waiting_query = State()


# ── Kino kodi yoki nom kiritilganda ───────────────────────────────────────────

async def _subscription_gate(
    message: Message,
    bot,
    session: AsyncSession,
    db_user: User,
    lang: str,
) -> bool:
    """
    Obunani tekshiradi. True — o'tishi mumkin, False — bloklangan.
    Adminlar har doim o'ta oladi.
    """
    is_privileged = (
        db_user.telegram_id in settings.super_admin_list
        or db_user.admin_profile is not None
    )
    if is_privileged:
        return True

    channels = await get_active_channels(session)
    if not channels:
        return True

    not_subscribed = await check_user_subscriptions(
        bot=bot, user_id=db_user.telegram_id, channels=channels
    )
    if not not_subscribed:
        return True

    await message.answer(
        get_text("subscription-required", lang),
        reply_markup=build_subscription_keyboard(not_subscribed, lang),
    )
    return False


@router.message(Command("search"))
@router.message(F.text.in_(_SEARCH_BTN))
async def cmd_search(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    db_user: User,
    lang: str,
    bot,
) -> None:
    """Qidiruv boshlash — /search yoki '🔍 Qidirish' tugmasi"""
    if not await _subscription_gate(message, bot, session, db_user, lang):
        return
    await message.answer(get_text("search-prompt", lang))
    await state.set_state(SearchState.waiting_query)


@router.message(SearchState.waiting_query)
async def process_search_query(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    lang: str,
) -> None:
    """Qidiruv so'rovini qayta ishlash"""
    query = message.text.strip()
    await state.clear()
    await _do_search(message, session, query, lang)


@router.message(F.text.regexp(r"^\d+$"))
async def process_movie_code(
    message: Message,
    session: AsyncSession,
    db_user: User,
    lang: str,
    bot,
) -> None:
    """Faqat raqam kiritilsa — kino kodi deb qabul qilamiz"""
    if not await _subscription_gate(message, bot, session, db_user, lang):
        return

    code = message.text.strip().upper()
    movie = await get_movie_by_code(session, code)

    if not movie:
        await message.answer(get_text("movie-not-found", lang, code=code))
        return

    await _send_movie(message, bot, session, movie, db_user, lang)


async def _do_search(
    message: Message,
    session: AsyncSession,
    query: str,
    lang: str,
    offset: int = 0,
) -> None:
    """Qidiruv bajarish va natijalarni ko'rsatish"""
    movies, total = await search_movies(session, query, limit=MOVIES_PER_PAGE, offset=offset)

    if not movies:
        await message.answer(get_text("search-no-results", lang, query=query))
        return

    # Natijalar xabari
    text = get_text("search-results-header", lang, query=query) + "\n\n"
    for i, movie in enumerate(movies, start=offset + 1):
        title = movie.get_title(lang)
        year = movie.year or ""
        text += get_text(
            "search-result-item", lang,
            num=i, title=title, year=year, code=movie.code
        ) + "\n"

    text += f"\n{get_text('search-select-prompt', lang)}"

    # Pagination keyboard
    keyboard = _build_search_results_keyboard(movies, query, offset, total, lang)

    await message.answer(text, reply_markup=keyboard)


def _build_search_results_keyboard(
    movies: list,
    query: str,
    offset: int,
    total: int,
    lang: str,
) -> InlineKeyboardMarkup:
    """Qidiruv natijalari klaviaturasi — tanlash + pagination"""
    builder = InlineKeyboardBuilder()

    # Har bir kino uchun tugma
    for movie in movies:
        title = movie.get_title(lang)
        builder.row(
            InlineKeyboardButton(
                text=f"🎬 {title[:40]}",
                callback_data=f"movie:{movie.code}",
            )
        )

    # Pagination
    nav_row = []
    # Prefixni 'p' (page) ga qisqartiramiz, 64-character limitni saqlash uchun
    if offset > 0:
        nav_row.append(
            InlineKeyboardButton(text="◀️", callback_data=f"p:{offset - MOVIES_PER_PAGE}:{query[:40]}")
        )
    if offset + MOVIES_PER_PAGE < total:
        nav_row.append(
            InlineKeyboardButton(text="▶️", callback_data=f"p:{offset + MOVIES_PER_PAGE}:{query[:40]}")
        )
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
) -> None:
    """Kino tanlanganda forward qilish"""
    code = callback.data.split(":")[1]
    movie = await get_movie_by_code(session, code)

    if not movie:
        await callback.answer(get_text("movie-not-found", lang, code=code), show_alert=True)
        return

    await _send_movie(callback.message, bot, session, movie, db_user, lang)
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("p:"))
async def process_search_pagination(
    callback: CallbackQuery,
    session: AsyncSession,
    lang: str,
) -> None:
    """Qidiruv paginatsiyasi (p:offset:query)"""
    parts = callback.data.split(":")
    offset = int(parts[1]) if len(parts) > 1 else 0
    query = parts[2] if len(parts) > 2 else ""

    # Message text'dan to'liq query'ni olishga harakat qilamiz (agar truncate qilingan bo'lsa)
    # search-results-header: 🎬 결과 (query): ...
    if callback.message.text and "🎬" in callback.message.text:
        try:
            # "🎬 Results for \"{query}\":" -> bizda l10n bor, shuning uchun biroz murakkab
            # Lekin query[:40] ham ko'p hollarda yetarli
            pass
        except:
            pass

    await callback.message.delete()
    await _do_search(callback.message, session, query, lang, offset)
    await callback.answer()


async def _send_movie(
    message: Message,
    bot,
    session: AsyncSession,
    movie: Movie,
    db_user: User,
    lang: str,
) -> None:
    """Kinoni forward qilish va ma'lumotini yuborish"""
    # Kino faylini kanaldan caption'siz jo'natish
    # aiogram caption="" ni serialize qilmasligi sababli to'g'ridan-to'g'ri API ishlatiladi
    try:
        url = f"https://api.telegram.org/bot{bot.token}/copyMessage"
        payload = {
            "chat_id": message.chat.id,
            "from_chat_id": settings.movie_channel_id,
            "message_id": movie.channel_message_id,
            "caption": "",
            "protect_content": True,
        }
        async with aiohttp.ClientSession() as http:
            async with http.post(url, json=payload) as resp:
                result = await resp.json()
                if not result.get("ok"):
                    raise Exception(result.get("description", "Noma'lum xato"))
    except Exception as e:
        await message.answer(f"⚠️ Kinoni yuklashda xatolik: {e}")
        return

    # Ko'rish statistikasini saqlash
    if db_user:
        await record_view(session, movie.id, db_user.id)

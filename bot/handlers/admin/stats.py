from aiogram import Router, F
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import User
from bot.database.crud.analytics import get_full_stats
from bot.handlers.admin.panel import is_admin
from bot.keyboards.admin_kb import build_back_to_panel_keyboard
from bot.services.i18n import get_text

router = Router(name="admin_stats")


@router.callback_query(F.data == "admin:stats")
async def callback_stats(
    callback: CallbackQuery,
    session: AsyncSession,
    db_user: User,
    lang: str,
) -> None:
    """Statistika ko'rsatish"""
    if not is_admin(callback.from_user.id, db_user):
        await callback.answer(get_text("access-denied", lang), show_alert=True)
        return

    await callback.answer("⏳")

    stats = await get_full_stats(session)
    users = stats["users"]
    movies = stats["movies"]
    by_lang = users.get("by_language", {})

    text = get_text(
        "stats", lang,
        total_users=users["total"],
        today_users=users["today"],
        week_users=users["week"],
        month_users=users["month"],
        active_7d=users["active_7d"],
        active_30d=users["active_30d"],
        banned=users["banned"],
        total_movies=movies["total"],
        total_views=movies["total_views"],
        lang_uz=by_lang.get("uz", 0),
        lang_ru=by_lang.get("ru", 0),
        lang_en=by_lang.get("en", 0),
    )

    # Top kinolar (10 ta)
    top_movies = movies.get("top_all_time", [])
    if top_movies:
        text += "\n\n🏆 <b>Top 10 kinolar:</b>\n"
        for i, (movie, views) in enumerate(top_movies, 1):
            title = movie.get_title(lang)
            text += f"{i}. {title} — <b>{views}</b> ko'rish\n"

    # Soatlik faollik
    hourly = movies.get("hourly_activity", {})
    if hourly:
        max_hour = max(hourly, key=hourly.get)
        text += f"\n⏰ <b>Eng faol soat:</b> {max_hour}:00 ({hourly[max_hour]} so'rov)"

    await callback.message.edit_text(
        text,
        reply_markup=build_back_to_panel_keyboard(lang),
    )

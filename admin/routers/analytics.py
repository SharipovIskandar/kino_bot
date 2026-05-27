from fastapi import APIRouter, Request
from sqlalchemy import select, func, desc
from datetime import datetime, timedelta, timezone

from admin.responses import render
from bot.database.connection import AsyncSessionFactory
from bot.database.crud.analytics import (
    get_daily_registrations,
    get_users_by_language,
    get_hourly_activity,
    get_top_movies,
)
from bot.database.models import MovieView

router = APIRouter()


async def _get_daily_views(session, days: int = 30):
    since = datetime.now(timezone.utc) - timedelta(days=days)
    result = await session.execute(
        select(
            func.date(MovieView.viewed_at).label("date"),
            func.count(MovieView.id).label("count"),
        )
        .where(MovieView.viewed_at >= since)
        .group_by(func.date(MovieView.viewed_at))
        .order_by(func.date(MovieView.viewed_at))
    )
    return [(str(row.date), row.count) for row in result.all()]


@router.get("")
async def analytics(request: Request):
    async with AsyncSessionFactory() as session:
        reg_30 = await get_daily_registrations(session, days=30)
        views_30 = await _get_daily_views(session, days=30)
        lang_dist = await get_users_by_language(session)
        hourly = await get_hourly_activity(session, days=7)
        top_movies = await get_top_movies(session, limit=10)

    # Fill missing dates for registrations
    reg_dict = dict(reg_30)
    views_dict = dict(views_30)

    dates = []
    reg_vals = []
    views_vals = []
    for i in range(29, -1, -1):
        d = (datetime.now(timezone.utc) - timedelta(days=i)).strftime("%Y-%m-%d")
        dates.append(d)
        reg_vals.append(reg_dict.get(d, 0))
        views_vals.append(views_dict.get(d, 0))

    hourly_labels = list(range(24))
    hourly_data = [hourly.get(h, 0) for h in hourly_labels]

    top_titles = [m.get_title("uz") for m, _ in top_movies]
    top_views = [v for _, v in top_movies]

    return render(
        request, "analytics/index.html",
        dates=dates,
        reg_vals=reg_vals,
        views_vals=views_vals,
        lang_labels=list(lang_dist.keys()),
        lang_data=list(lang_dist.values()),
        hourly_labels=[f"{h}:00" for h in hourly_labels],
        hourly_data=hourly_data,
        top_titles=top_titles,
        top_views=top_views,
    )

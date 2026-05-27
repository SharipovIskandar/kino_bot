from fastapi import APIRouter, Request
from sqlalchemy.ext.asyncio import AsyncSession

from admin.responses import render
from bot.database.connection import AsyncSessionFactory
from bot.database.crud.analytics import (
    get_total_users,
    get_total_movies,
    get_total_views,
    get_new_users_count,
    get_active_users_count,
    get_banned_users_count,
    get_daily_registrations,
    get_top_movies,
)

router = APIRouter()


@router.get("/dashboard")
async def dashboard(request: Request):
    async with AsyncSessionFactory() as session:
        total_users = await get_total_users(session)
        total_movies = await get_total_movies(session)
        total_views = await get_total_views(session)
        new_today = await get_new_users_count(session, days=1)
        new_week = await get_new_users_count(session, days=7)
        active_7d = await get_active_users_count(session, days=7)
        banned = await get_banned_users_count(session)
        reg_chart = await get_daily_registrations(session, days=14)
        top_movies = await get_top_movies(session, limit=10)

    reg_labels = [r[0] for r in reg_chart]
    reg_data = [r[1] for r in reg_chart]

    return render(
        request,
        "dashboard/index.html",
        total_users=total_users,
        total_movies=total_movies,
        total_views=total_views,
        new_today=new_today,
        new_week=new_week,
        active_7d=active_7d,
        banned=banned,
        reg_labels=reg_labels,
        reg_data=reg_data,
        top_movies=top_movies,
    )

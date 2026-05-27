from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple

from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import User, Movie, MovieView, MandatoryChannel, Language


# ── Foydalanuvchilar statistikasi ─────────────────────────────────────────────

async def get_total_users(session: AsyncSession) -> int:
    result = await session.execute(select(func.count(User.id)))
    return result.scalar_one()


async def get_new_users_count(session: AsyncSession, days: int = 1) -> int:
    """Oxirgi N kunda yangi userlar soni"""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    result = await session.execute(
        select(func.count(User.id)).where(User.registered_at >= since)
    )
    return result.scalar_one()


async def get_active_users_count(session: AsyncSession, days: int = 30) -> int:
    """Oxirgi N kunda faol userlar soni"""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    result = await session.execute(
        select(func.count(User.id)).where(User.last_active_at >= since)
    )
    return result.scalar_one()


async def get_banned_users_count(session: AsyncSession) -> int:
    result = await session.execute(
        select(func.count(User.id)).where(User.is_banned == True)
    )
    return result.scalar_one()


async def get_users_by_language(session: AsyncSession) -> dict[str, int]:
    """Tillar bo'yicha user taqsimoti"""
    result = await session.execute(
        select(User.language, func.count(User.id))
        .group_by(User.language)
    )
    return {row[0].value: row[1] for row in result.all()}


async def get_daily_registrations(
    session: AsyncSession, days: int = 7
) -> List[Tuple[str, int]]:
    """Oxirgi N kun uchun kunlik ro'yxatdan o'tishlar"""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    result = await session.execute(
        select(
            func.date(User.registered_at).label("date"),
            func.count(User.id).label("count"),
        )
        .where(User.registered_at >= since)
        .group_by(func.date(User.registered_at))
        .order_by(func.date(User.registered_at))
    )
    return [(str(row.date), row.count) for row in result.all()]


# ── Kinolar statistikasi ───────────────────────────────────────────────────────

async def get_total_movies(session: AsyncSession, only_active: bool = True) -> int:
    q = select(func.count(Movie.id))
    if only_active:
        q = q.where(Movie.is_active == True)
    result = await session.execute(q)
    return result.scalar_one()


async def get_top_movies(
    session: AsyncSession, limit: int = 10, days: Optional[int] = None
) -> List[Tuple[Movie, int]]:
    """
    Eng ko'p so'ralgan kinolar.
    days berilsa — oxirgi N kun ichida.
    """
    if days:
        since = datetime.now(timezone.utc) - timedelta(days=days)
        result = await session.execute(
            select(Movie, func.count(MovieView.id).label("views"))
            .join(MovieView, Movie.id == MovieView.movie_id)
            .where(Movie.is_active == True, MovieView.viewed_at >= since)
            .group_by(Movie.id)
            .order_by(func.count(MovieView.id).desc())
            .limit(limit)
        )
    else:
        result = await session.execute(
            select(Movie)
            .where(Movie.is_active == True)
            .order_by(Movie.view_count.desc())
            .limit(limit)
        )
        return [(movie, movie.view_count) for movie in result.scalars().all()]

    return [(row.Movie, row.views) for row in result.all()]


async def get_hourly_activity(session: AsyncSession, days: int = 7) -> dict[int, int]:
    """Soat bo'yicha faollik (peak hours) — oxirgi N kun"""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    result = await session.execute(
        select(
            func.extract("hour", MovieView.viewed_at).label("hour"),
            func.count(MovieView.id).label("count"),
        )
        .where(MovieView.viewed_at >= since)
        .group_by(func.extract("hour", MovieView.viewed_at))
        .order_by(func.extract("hour", MovieView.viewed_at))
    )
    return {int(row.hour): row.count for row in result.all()}


async def get_total_views(session: AsyncSession) -> int:
    result = await session.execute(select(func.count(MovieView.id)))
    return result.scalar_one()


# ── To'liq statistika paketi ──────────────────────────────────────────────────

async def get_full_stats(session: AsyncSession) -> dict:
    """Admin uchun to'liq statistika"""
    return {
        "users": {
            "total": await get_total_users(session),
            "today": await get_new_users_count(session, days=1),
            "week": await get_new_users_count(session, days=7),
            "month": await get_new_users_count(session, days=30),
            "active_7d": await get_active_users_count(session, days=7),
            "active_30d": await get_active_users_count(session, days=30),
            "banned": await get_banned_users_count(session),
            "by_language": await get_users_by_language(session),
        },
        "movies": {
            "total": await get_total_movies(session),
            "total_views": await get_total_views(session),
            "top_today": await get_top_movies(session, limit=5, days=1),
            "top_week": await get_top_movies(session, limit=5, days=7),
            "top_all_time": await get_top_movies(session, limit=10),
            "hourly_activity": await get_hourly_activity(session, days=7),
        },
    }

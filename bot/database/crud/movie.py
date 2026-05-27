from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import select, update, func, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from bot.database.models import Movie, MovieView, Genre


async def get_movie_by_code(session: AsyncSession, code: str) -> Optional[Movie]:
    """Kino kodiga qarab topish"""
    result = await session.execute(
        select(Movie)
        .where(Movie.code == code.upper(), Movie.is_active == True)
        .options(selectinload(Movie.genres))
    )
    return result.scalar_one_or_none()


async def search_movies(
    session: AsyncSession,
    query: str,
    limit: int = 10,
    offset: int = 0,
) -> tuple[List[Movie], int]:
    """
    Nom yoki kod bo'yicha qidirish (case-insensitive).
    Returns: (movies, total_count)
    """
    search = f"%{query}%"
    base_query = (
        select(Movie)
        .where(
            Movie.is_active == True,
            or_(
                Movie.code.ilike(search),
                Movie.title_uz.ilike(search),
                Movie.title_ru.ilike(search),
                Movie.title_en.ilike(search),
            ),
        )
        .options(selectinload(Movie.genres))
    )

    # Total count
    count_result = await session.execute(
        select(func.count()).select_from(base_query.subquery())
    )
    total = count_result.scalar_one()

    # Paginated results
    result = await session.execute(
        base_query.order_by(desc(Movie.view_count)).limit(limit).offset(offset)
    )
    movies = result.scalars().all()
    return list(movies), total


async def upsert_movie(
    session: AsyncSession,
    code: str,
    channel_message_id: int,
    **kwargs,
) -> tuple[Movie, bool]:
    """
    Kinoni qo'shish yoki yangilash (sync uchun).
    Returns: (movie, created)
    """
    existing = await session.execute(
        select(Movie).where(Movie.code == code)
    )
    movie = existing.scalar_one_or_none()

    if movie:
        # Yangilash
        movie.channel_message_id = channel_message_id
        movie.synced_at = datetime.now(timezone.utc)
        for key, value in kwargs.items():
            if hasattr(movie, key) and value is not None:
                setattr(movie, key, value)
        await session.commit()
        return movie, False
    else:
        # Yaratish
        movie = Movie(
            code=code.upper(),
            channel_message_id=channel_message_id,
            synced_at=datetime.now(timezone.utc),
            **kwargs,
        )
        session.add(movie)
        await session.commit()
        await session.refresh(movie)
        return movie, True


async def delete_movie(session: AsyncSession, code: str) -> bool:
    """Kinoni o'chirish (soft delete). Returns True agar topilsa"""
    result = await session.execute(select(Movie).where(Movie.code == code))
    movie = result.scalar_one_or_none()
    if not movie:
        return False
    movie.is_active = False
    await session.commit()
    return True


async def record_view(
    session: AsyncSession, movie_id: int, user_id: int
) -> None:
    """Ko'rish statistikasini saqlash (takrorlanishdan himoyalangan)"""
    # Avval shu user shu kinoni ko'rgan-ko'rmaganini tekshiramiz
    existing = await session.execute(
        select(MovieView).where(
            MovieView.movie_id == movie_id,
            MovieView.user_id == user_id
        )
    )
    if existing.scalar_one_or_none():
        return

    # movie_views jadvaliga yozish
    view = MovieView(movie_id=movie_id, user_id=user_id)
    session.add(view)
    
    # view_count oshirish
    await session.execute(
        update(Movie)
        .where(Movie.id == movie_id)
        .values(view_count=Movie.view_count + 1)
    )
    await session.commit()


async def get_movies_paginated(
    session: AsyncSession,
    limit: int = 10,
    offset: int = 0,
    only_active: bool = True,
) -> tuple[List[Movie], int]:
    """Admin uchun: barcha kinolar ro'yxati"""
    base_q = select(Movie)
    if only_active:
        base_q = base_q.where(Movie.is_active == True)

    count_result = await session.execute(
        select(func.count()).select_from(base_q.subquery())
    )
    total = count_result.scalar_one()

    result = await session.execute(
        base_q.order_by(desc(Movie.created_at)).limit(limit).offset(offset)
    )
    return list(result.scalars().all()), total


async def get_top_movies(
    session: AsyncSession, limit: int = 10
) -> List[Movie]:
    """Eng ko'p ko'rilgan kinolar"""
    result = await session.execute(
        select(Movie)
        .where(Movie.is_active == True)
        .order_by(desc(Movie.view_count))
        .limit(limit)
        .options(selectinload(Movie.genres))
    )
    return list(result.scalars().all())

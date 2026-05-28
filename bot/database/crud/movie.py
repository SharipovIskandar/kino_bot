import re
from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import select, update, func, or_, desc
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from bot.database.models import Movie, MovieView, Genre, MovieGenre


# ── Genre yordamchi funksiyasi ────────────────────────────────────────────────

def _slugify(name: str) -> str:
    """Janr nomidan slug yaratish"""
    slug = name.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_-]+", "_", slug)
    return slug[:64]


async def get_or_create_genre(session: AsyncSession, genre_name: str) -> Genre:
    """Janrni topish yoki yaratish"""
    slug = _slugify(genre_name)
    result = await session.execute(select(Genre).where(Genre.slug == slug))
    genre = result.scalar_one_or_none()
    if not genre:
        genre = Genre(name=genre_name.strip(), slug=slug)
        session.add(genre)
        await session.flush()
        await session.refresh(genre)
    return genre


# ── Asosiy CRUD funksiyalar ───────────────────────────────────────────────────

async def get_movie_by_code(session: AsyncSession, code: str) -> Optional[Movie]:
    """Kino kodiga qarab topish"""
    result = await session.execute(
        select(Movie)
        .where(Movie.code == code.upper().strip(), Movie.is_active == True)
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
                Movie.title.ilike(search),
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
    genres: list | None = None,
    **kwargs,
) -> tuple[Movie, bool]:
    """
    Kinoni qo'shish yoki yangilash.
    Avval code bo'yicha, keyin channel_message_id bo'yicha izlaydi.
    Returns: (movie, created)
    """
    code = code.upper().strip()

    # 1. Code bo'yicha izlash
    result = await session.execute(
        select(Movie).where(Movie.code == code)
    )
    movie = result.scalar_one_or_none()

    # 2. channel_message_id bo'yicha izlash (agar code bo'yicha topilmasa)
    if movie is None:
        result = await session.execute(
            select(Movie).where(Movie.channel_message_id == channel_message_id)
        )
        movie = result.scalar_one_or_none()

    if movie:
        # Yangilash
        movie.code = code
        movie.channel_message_id = channel_message_id
        movie.synced_at = datetime.now(timezone.utc)
        for key, value in kwargs.items():
            if hasattr(movie, key) and value is not None:
                setattr(movie, key, value)
        await session.flush()

        # Janrlarni yangilash
        if genres is not None:
            await _sync_movie_genres(session, movie, genres)

        return movie, False
    else:
        # Yaratish
        movie = Movie(
            code=code,
            channel_message_id=channel_message_id,
            synced_at=datetime.now(timezone.utc),
            **kwargs,
        )
        session.add(movie)
        await session.flush()
        await session.refresh(movie)

        # Janrlarni saqlash
        if genres:
            await _sync_movie_genres(session, movie, genres)

        return movie, True


async def _sync_movie_genres(
    session: AsyncSession,
    movie: Movie,
    genre_names: list[str],
) -> None:
    """Kinoning janrlarini yangilash"""
    if not genre_names:
        return

    # Mavjud bog'lanishlarni o'chirish
    from sqlalchemy import delete as sa_delete
    await session.execute(
        sa_delete(MovieGenre).where(MovieGenre.movie_id == movie.id)
    )

    # Yangi janrlarni qo'shish
    for genre_name in genre_names:
        if not genre_name.strip():
            continue
        genre = await get_or_create_genre(session, genre_name)
        session.add(MovieGenre(movie_id=movie.id, genre_id=genre.id))

    await session.flush()


async def delete_movie(session: AsyncSession, code: str) -> bool:
    """Kinoni o'chirish (soft delete). Returns True agar topilsa"""
    result = await session.execute(select(Movie).where(Movie.code == code.upper().strip()))
    movie = result.scalar_one_or_none()
    if not movie:
        return False
    movie.is_active = False
    await session.flush()
    return True


async def record_view(
    session: AsyncSession, movie_id: int, user_id: int
) -> bool:
    """Ko'rish statistikasini saqlash. True = yangi ko'rish, False = takror."""
    stmt = (
        pg_insert(MovieView)
        .values(movie_id=movie_id, user_id=user_id)
        .on_conflict_do_nothing(constraint="uq_movie_views_user_movie")
    )
    result = await session.execute(stmt)
    if result.rowcount > 0:
        await session.execute(
            update(Movie)
            .where(Movie.id == movie_id)
            .values(view_count=Movie.view_count + 1)
        )
        return True
    return False


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


async def get_random_movie(session: AsyncSession) -> Optional[Movie]:
    """Tasodifiy faol kino"""
    result = await session.execute(
        select(Movie)
        .where(Movie.is_active == True)
        .order_by(func.random())
        .limit(1)
        .options(selectinload(Movie.genres))
    )
    return result.scalar_one_or_none()


async def get_popular_movies(session: AsyncSession, limit: int = 5) -> List[Movie]:
    """Ko'rishlar soni bo'yicha mashhur kinolar"""
    result = await session.execute(
        select(Movie)
        .where(Movie.is_active == True)
        .order_by(desc(Movie.view_count))
        .limit(limit)
        .options(selectinload(Movie.genres))
    )
    return list(result.scalars().all())

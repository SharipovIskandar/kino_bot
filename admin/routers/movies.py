import math
from typing import Annotated, List, Optional

from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from sqlalchemy import select, func, or_, desc, delete
from sqlalchemy.orm import selectinload

from admin.responses import render
from bot.database.connection import AsyncSessionFactory
from bot.database.models import Movie, Genre, MovieGenre, AdminAction, MovieLanguageType

router = APIRouter()
PER_PAGE = 20


def _redirect(url: str, msg: str = "", type_: str = "success") -> RedirectResponse:
    sep = "&" if "?" in url else "?"
    return RedirectResponse(f"{url}{sep}msg={msg}&type={type_}", status_code=302)


@router.get("")
async def movie_list(request: Request, page: int = 1, q: str = "", active: str = "all"):
    offset = (page - 1) * PER_PAGE
    async with AsyncSessionFactory() as session:
        base = select(Movie).options(selectinload(Movie.genres))
        if q:
            s = f"%{q}%"
            base = base.where(
                or_(Movie.code.ilike(s), Movie.title.ilike(s))
            )
        if active == "active":
            base = base.where(Movie.is_active == True)
        elif active == "inactive":
            base = base.where(Movie.is_active == False)

        total_r = await session.execute(select(func.count()).select_from(base.subquery()))
        total = total_r.scalar_one()
        movies_r = await session.execute(base.order_by(desc(Movie.created_at)).limit(PER_PAGE).offset(offset))
        movies = list(movies_r.scalars().all())

    return render(
        request, "movies/list.html",
        movies=movies, total=total, page=page,
        total_pages=math.ceil(total / PER_PAGE) if total else 1,
        q=q, active=active,
    )


@router.get("/new")
async def movie_new(request: Request):
    async with AsyncSessionFactory() as session:
        genres_r = await session.execute(select(Genre).order_by(Genre.name))
        genres = list(genres_r.scalars().all())
    return render(request, "movies/form.html", movie=None, genres=genres,
                  language_types=list(MovieLanguageType))


@router.post("/new")
async def movie_create(
    request: Request,
    code: str = Form(...),
    channel_message_id: int = Form(...),
    title: str = Form(""),
    description: str = Form(""),
    year: Optional[int] = Form(None), duration: Optional[int] = Form(None),
    country: str = Form(""), director: str = Form(""), cast: str = Form(""),
    imdb_rating: Optional[float] = Form(None), kinopoisk_rating: Optional[float] = Form(None),
    age_rating: str = Form(""), language_type: str = Form(""),
    genre_ids: Annotated[Optional[List[str]], Form()] = None,
):
    genre_ids = genre_ids or []
    code = code.upper().strip()
    async with AsyncSessionFactory() as session:
        existing = await session.execute(select(Movie).where(Movie.code == code))
        if existing.scalar_one_or_none():
            genres_r = await session.execute(select(Genre).order_by(Genre.name))
            return render(request, "movies/form.html", movie=None,
                          genres=list(genres_r.scalars().all()),
                          language_types=list(MovieLanguageType),
                          error=f"'{code}' kodi allaqachon mavjud")

        movie = Movie(
            code=code, channel_message_id=channel_message_id,
            title=title or None,
            description=description or None,
            year=year, duration=duration,
            country=country or None, director=director or None, cast=cast or None,
            imdb_rating=imdb_rating, kinopoisk_rating=kinopoisk_rating,
            age_rating=age_rating or None,
            language_type=MovieLanguageType(language_type) if language_type else None,
        )
        session.add(movie)
        await session.flush()

        for gid in genre_ids:
            session.add(MovieGenre(movie_id=movie.id, genre_id=int(gid)))

        admin = request.state.admin
        session.add(AdminAction(
            admin_telegram_id=int(admin["sub"]),
            action_type="movie_create",
            target_id=code,
            details={"title": title},
        ))
        await session.commit()

    return _redirect("/movies", f"Kino '{code}' qo'shildi")


@router.get("/{movie_id}/edit")
async def movie_edit(request: Request, movie_id: int):
    async with AsyncSessionFactory() as session:
        movie_r = await session.execute(
            select(Movie).where(Movie.id == movie_id).options(selectinload(Movie.genres))
        )
        movie = movie_r.scalar_one_or_none()
        if not movie:
            return _redirect("/movies", "Kino topilmadi", "danger")

        genres_r = await session.execute(select(Genre).order_by(Genre.name))
        genres = list(genres_r.scalars().all())

    return render(request, "movies/form.html", movie=movie, genres=genres,
                  language_types=list(MovieLanguageType))


@router.post("/{movie_id}/edit")
async def movie_update(
    request: Request, movie_id: int,
    channel_message_id: int = Form(...),
    title: str = Form(""),
    description: str = Form(""),
    year: Optional[int] = Form(None), duration: Optional[int] = Form(None),
    country: str = Form(""), director: str = Form(""), cast: str = Form(""),
    imdb_rating: Optional[float] = Form(None), kinopoisk_rating: Optional[float] = Form(None),
    age_rating: str = Form(""), language_type: str = Form(""),
    genre_ids: Annotated[Optional[List[str]], Form()] = None,
):
    genre_ids = genre_ids or []
    async with AsyncSessionFactory() as session:
        movie_r = await session.execute(select(Movie).where(Movie.id == movie_id))
        movie = movie_r.scalar_one_or_none()
        if not movie:
            return _redirect("/movies", "Kino topilmadi", "danger")

        movie.channel_message_id = channel_message_id
        movie.title = title or None
        movie.description = description or None
        movie.year = year
        movie.duration = duration
        movie.country = country or None
        movie.director = director or None
        movie.cast = cast or None
        movie.imdb_rating = imdb_rating
        movie.kinopoisk_rating = kinopoisk_rating
        movie.age_rating = age_rating or None
        movie.language_type = MovieLanguageType(language_type) if language_type else None

        await session.execute(delete(MovieGenre).where(MovieGenre.movie_id == movie_id))
        for gid in genre_ids:
            session.add(MovieGenre(movie_id=movie_id, genre_id=int(gid)))

        admin = request.state.admin
        session.add(AdminAction(
            admin_telegram_id=int(admin["sub"]),
            action_type="movie_update",
            target_id=movie.code,
        ))
        await session.commit()

    return _redirect("/movies", f"Kino '{movie.code}' yangilandi")


@router.post("/{movie_id}/toggle")
async def movie_toggle(request: Request, movie_id: int):
    async with AsyncSessionFactory() as session:
        movie_r = await session.execute(select(Movie).where(Movie.id == movie_id))
        movie = movie_r.scalar_one_or_none()
        if not movie:
            return _redirect("/movies", "Kino topilmadi", "danger")
        movie.is_active = not movie.is_active
        status = "faollashtirildi" if movie.is_active else "o'chirildi"
        admin = request.state.admin
        session.add(AdminAction(
            admin_telegram_id=int(admin["sub"]),
            action_type="movie_toggle",
            target_id=movie.code,
            details={"is_active": movie.is_active},
        ))
        await session.commit()
    return _redirect("/movies", f"Kino '{movie.code}' {status}")


@router.post("/{movie_id}/delete")
async def movie_delete(request: Request, movie_id: int):
    async with AsyncSessionFactory() as session:
        movie_r = await session.execute(select(Movie).where(Movie.id == movie_id))
        movie = movie_r.scalar_one_or_none()
        if not movie:
            return _redirect("/movies", "Kino topilmadi", "danger")
        code = movie.code
        movie.is_active = False
        admin = request.state.admin
        session.add(AdminAction(
            admin_telegram_id=int(admin["sub"]),
            action_type="movie_delete",
            target_id=code,
        ))
        await session.commit()
    return _redirect("/movies", f"Kino '{code}' o'chirildi")

import math

from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from sqlalchemy import select, func, or_, desc
from sqlalchemy.orm import selectinload

from admin.responses import render
from bot.database.connection import AsyncSessionFactory
from bot.database.models import User, AdminAction, MovieView, Movie
from bot.database.crud.user import ban_user, unban_user

router = APIRouter()
PER_PAGE = 25


def _redirect(url: str, msg: str = "", type_: str = "success") -> RedirectResponse:
    sep = "&" if "?" in url else "?"
    return RedirectResponse(f"{url}{sep}msg={msg}&type={type_}", status_code=302)


@router.get("")
async def user_list(request: Request, page: int = 1, q: str = "", filter: str = "all"):
    offset = (page - 1) * PER_PAGE
    async with AsyncSessionFactory() as session:
        base = select(User).options(selectinload(User.admin_profile))
        if q:
            s = f"%{q}%"
            try:
                tid = int(q)
                base = base.where(
                    or_(User.telegram_id == tid, User.full_name.ilike(s), User.username.ilike(s))
                )
            except ValueError:
                base = base.where(
                    or_(User.full_name.ilike(s), User.username.ilike(s))
                )
        if filter == "banned":
            base = base.where(User.is_banned == True)
        elif filter == "active":
            base = base.where(User.is_banned == False)

        total_r = await session.execute(select(func.count()).select_from(base.subquery()))
        total = total_r.scalar_one()
        users_r = await session.execute(
            base.order_by(desc(User.registered_at)).limit(PER_PAGE).offset(offset)
        )
        users = list(users_r.scalars().all())

    return render(
        request, "users/list.html",
        users=users, total=total, page=page,
        total_pages=math.ceil(total / PER_PAGE) if total else 1,
        q=q, filter=filter,
    )


@router.get("/{telegram_id}")
async def user_detail(request: Request, telegram_id: int):
    async with AsyncSessionFactory() as session:
        user_r = await session.execute(
            select(User)
            .where(User.telegram_id == telegram_id)
            .options(selectinload(User.admin_profile))
        )
        user = user_r.scalar_one_or_none()
        if not user:
            return _redirect("/users", "Foydalanuvchi topilmadi", "danger")

        views_r = await session.execute(
            select(MovieView, Movie)
            .join(Movie, MovieView.movie_id == Movie.id)
            .where(MovieView.user_id == user.id)
            .order_by(desc(MovieView.viewed_at))
            .limit(20)
        )
        recent_views = [(row.MovieView, row.Movie) for row in views_r.all()]

        view_count_r = await session.execute(
            select(func.count()).where(MovieView.user_id == user.id)
        )
        total_views = view_count_r.scalar_one()

    return render(request, "users/detail.html",
                  user=user, recent_views=recent_views, total_views=total_views)


@router.post("/{telegram_id}/ban")
async def user_ban(request: Request, telegram_id: int, reason: str = Form("")):
    admin = request.state.admin
    async with AsyncSessionFactory() as session:
        ok = await ban_user(session, telegram_id, reason or "Admin tomonidan ban qilindi",
                            int(admin["sub"]))
        if ok:
            session.add(AdminAction(
                admin_telegram_id=int(admin["sub"]),
                action_type="user_ban",
                target_id=str(telegram_id),
                details={"reason": reason},
            ))
            await session.commit()
    msg = f"Foydalanuvchi {telegram_id} ban qilindi" if ok else "Foydalanuvchi topilmadi"
    return _redirect(f"/users/{telegram_id}", msg, "success" if ok else "danger")


@router.post("/{telegram_id}/unban")
async def user_unban(request: Request, telegram_id: int):
    admin = request.state.admin
    async with AsyncSessionFactory() as session:
        ok = await unban_user(session, telegram_id)
        if ok:
            session.add(AdminAction(
                admin_telegram_id=int(admin["sub"]),
                action_type="user_unban",
                target_id=str(telegram_id),
            ))
            await session.commit()
    msg = f"Foydalanuvchi {telegram_id} ban olib tashlandi" if ok else "Foydalanuvchi topilmadi"
    return _redirect(f"/users/{telegram_id}", msg, "success" if ok else "danger")

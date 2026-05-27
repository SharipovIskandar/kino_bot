from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from sqlalchemy import select

from admin.responses import render
from bot.config import settings
from bot.database.connection import AsyncSessionFactory
from bot.database.models import AdminAction, AdminRole
from bot.database.crud.admin import (
    get_all_admins, add_admin, remove_admin, update_admin_role,
    get_admin_by_telegram_id,
)
from bot.database.crud.user import get_user

router = APIRouter()


def _redirect(url: str, msg: str = "", type_: str = "success") -> RedirectResponse:
    sep = "&" if "?" in url else "?"
    return RedirectResponse(f"{url}{sep}msg={msg}&type={type_}", status_code=302)


@router.get("")
async def admin_list(request: Request):
    async with AsyncSessionFactory() as session:
        admins = await get_all_admins(session)
    return render(request, "admins/list.html",
                  admins=admins, roles=list(AdminRole))


@router.post("/add")
async def admin_add(
    request: Request,
    telegram_id: int = Form(...),
    role: str = Form(...),
):
    current = request.state.admin
    if current["role"] not in ("super_admin",):
        return _redirect("/admins", "Ruxsat yo'q", "danger")

    async with AsyncSessionFactory() as session:
        user = await get_user(session, telegram_id)
        if not user:
            return _redirect("/admins", "Telegram ID bo'yicha foydalanuvchi topilmadi", "danger")

        existing = await get_admin_by_telegram_id(session, telegram_id)
        if existing:
            return _redirect("/admins", "Bu foydalanuvchi allaqachon admin", "warning")

        await add_admin(session, user, AdminRole(role), int(current["sub"]))
        session.add(AdminAction(
            admin_telegram_id=int(current["sub"]),
            action_type="admin_add",
            target_id=str(telegram_id),
            details={"role": role},
        ))
        await session.commit()

    return _redirect("/admins", f"Admin {telegram_id} qo'shildi")


@router.post("/{telegram_id}/role")
async def admin_change_role(
    request: Request,
    telegram_id: int,
    role: str = Form(...),
):
    current = request.state.admin
    if current["role"] not in ("super_admin",):
        return _redirect("/admins", "Ruxsat yo'q", "danger")

    async with AsyncSessionFactory() as session:
        ok = await update_admin_role(session, telegram_id, AdminRole(role))
        if ok:
            session.add(AdminAction(
                admin_telegram_id=int(current["sub"]),
                action_type="admin_role_change",
                target_id=str(telegram_id),
                details={"new_role": role},
            ))
            await session.commit()

    msg = "Rol yangilandi" if ok else "Admin topilmadi"
    return _redirect("/admins", msg, "success" if ok else "danger")


@router.post("/{telegram_id}/remove")
async def admin_remove(request: Request, telegram_id: int):
    current = request.state.admin
    if current["role"] not in ("super_admin",):
        return _redirect("/admins", "Ruxsat yo'q", "danger")
    if int(current["sub"]) == telegram_id:
        return _redirect("/admins", "O'zingizni o'chira olmaysiz", "danger")

    async with AsyncSessionFactory() as session:
        ok = await remove_admin(session, telegram_id)
        if ok:
            session.add(AdminAction(
                admin_telegram_id=int(current["sub"]),
                action_type="admin_remove",
                target_id=str(telegram_id),
            ))
            await session.commit()

    msg = f"Admin {telegram_id} o'chirildi" if ok else "Admin topilmadi"
    return _redirect("/admins", msg, "success" if ok else "danger")

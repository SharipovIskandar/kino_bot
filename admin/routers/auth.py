import time
from collections import defaultdict

from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse, JSONResponse

from admin.auth import create_access_token
from admin.responses import render
from bot.config import settings
from bot.database.connection import AsyncSessionFactory
from bot.database.crud.admin import get_admin_by_telegram_id

router = APIRouter()

# In-memory rate limit store: {ip: [timestamp, ...]}
_login_attempts: dict = defaultdict(list)
MAX_ATTEMPTS = 5
LOCKOUT_SECONDS = 900  # 15 minutes


def _check_rate_limit(ip: str) -> bool:
    """Returns True if request is allowed, False if rate limited"""
    now = time.time()
    attempts = _login_attempts[ip]
    # Remove old attempts outside window
    _login_attempts[ip] = [t for t in attempts if now - t < LOCKOUT_SECONDS]
    return len(_login_attempts[ip]) < MAX_ATTEMPTS


def _record_failed_attempt(ip: str):
    _login_attempts[ip].append(time.time())


@router.get("/login")
async def login_page(request: Request):
    return render(request, "login.html")


@router.post("/login")
async def login(
    request: Request,
    telegram_id: int = Form(...),
    password: str = Form(...),
):
    client_ip = request.client.host
    if not _check_rate_limit(client_ip):
        return render(
            request,
            "login.html",
            error="Juda ko'p urinish. 15 daqiqadan so'ng qayta urinib ko'ring.",
        )

    if password != settings.admin_web_password:
        _record_failed_attempt(client_ip)
        return render(request, "login.html", error="Noto'g'ri parol")

    async with AsyncSessionFactory() as session:
        admin = await get_admin_by_telegram_id(session, telegram_id)

    is_super = telegram_id in settings.super_admin_list
    if not admin and not is_super:
        _record_failed_attempt(client_ip)
        return render(request, "login.html", error="Siz admin emassiz")

    role = "super_admin" if is_super else admin.role.value
    name = admin.user.full_name if admin else f"SuperAdmin #{telegram_id}"

    token = create_access_token(telegram_id, role, name, settings.admin_secret_key)

    response = RedirectResponse(url="/dashboard", status_code=302)
    response.set_cookie(
        key="admin_token",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=86400,
        secure=settings.admin_cookie_secure,
    )
    return response


@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/auth/login", status_code=302)
    response.delete_cookie("admin_token")
    return response

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware

from admin.auth import verify_token
from bot.config import settings


# ── Auth Middleware ───────────────────────────────────────────────────────────

PUBLIC_PATHS = {"/auth/login", "/auth/logout"}


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in PUBLIC_PATHS:
            return await call_next(request)

        token = request.cookies.get("admin_token")
        if not token:
            return RedirectResponse(url="/auth/login", status_code=302)

        payload = verify_token(token, settings.admin_secret_key)
        if not payload:
            resp = RedirectResponse(url="/auth/login", status_code=302)
            resp.delete_cookie("admin_token")
            return resp

        request.state.admin = payload
        return await call_next(request)


# ── App ───────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="KinoBot Admin Panel",
    docs_url=None,
    redoc_url=None,
    lifespan=lifespan,
)

app.add_middleware(AuthMiddleware)

# ── Routers ───────────────────────────────────────────────────────────────────

from admin.routers import (  # noqa: E402
    auth as auth_router,
    dashboard as dashboard_router,
    movies as movies_router,
    users as users_router,
    admins as admins_router,
    channels as channels_router,
    broadcast as broadcast_router,
    analytics as analytics_router,
    audit as audit_router,
)

app.include_router(auth_router.router, prefix="/auth")
app.include_router(dashboard_router.router)
app.include_router(movies_router.router, prefix="/movies")
app.include_router(users_router.router, prefix="/users")
app.include_router(admins_router.router, prefix="/admins")
app.include_router(channels_router.router, prefix="/channels")
app.include_router(broadcast_router.router, prefix="/broadcast")
app.include_router(analytics_router.router, prefix="/analytics")
app.include_router(audit_router.router, prefix="/audit")


@app.get("/")
async def root():
    return RedirectResponse(url="/dashboard")

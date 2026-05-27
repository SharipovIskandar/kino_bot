import math

from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from sqlalchemy import select, func, desc
from typing import Optional

from admin.responses import render
from bot.database.connection import AsyncSessionFactory
from bot.database.models import BroadcastMessage, BroadcastTarget, BroadcastStatus, MediaType

router = APIRouter()
PER_PAGE = 20


def _redirect(url: str, msg: str = "", type_: str = "success") -> RedirectResponse:
    sep = "&" if "?" in url else "?"
    return RedirectResponse(f"{url}{sep}msg={msg}&type={type_}", status_code=302)


@router.get("")
async def broadcast_list(request: Request, page: int = 1):
    offset = (page - 1) * PER_PAGE
    async with AsyncSessionFactory() as session:
        total_r = await session.execute(select(func.count(BroadcastMessage.id)))
        total = total_r.scalar_one()
        broadcasts_r = await session.execute(
            select(BroadcastMessage)
            .order_by(desc(BroadcastMessage.created_at))
            .limit(PER_PAGE).offset(offset)
        )
        broadcasts = list(broadcasts_r.scalars().all())

    return render(
        request, "broadcast/list.html",
        broadcasts=broadcasts, total=total, page=page,
        total_pages=math.ceil(total / PER_PAGE) if total else 1,
        BroadcastStatus=BroadcastStatus,
    )


@router.get("/create")
async def broadcast_create_page(request: Request):
    return render(request, "broadcast/create.html",
                  targets=list(BroadcastTarget))


@router.post("/create")
async def broadcast_create(
    request: Request,
    text: str = Form(""),
    target: str = Form("all"),
    media_file_id: str = Form(""),
    media_type: str = Form(""),
):
    if not text.strip() and not media_file_id.strip():
        return render(request, "broadcast/create.html",
                      targets=list(BroadcastTarget),
                      error="Matn yoki media fayl kiritilishi kerak")

    admin = request.state.admin
    async with AsyncSessionFactory() as session:
        broadcast = BroadcastMessage(
            text=text.strip() or None,
            media_file_id=media_file_id.strip() or None,
            media_type=MediaType(media_type) if media_type else None,
            target=BroadcastTarget(target),
            status=BroadcastStatus.PENDING,
            created_by=int(admin["sub"]),
        )
        session.add(broadcast)
        await session.commit()

    return _redirect("/broadcast", "Broadcast yaratildi. Telegram bot orqali yuboring.")


@router.post("/{broadcast_id}/cancel")
async def broadcast_cancel(request: Request, broadcast_id: int):
    async with AsyncSessionFactory() as session:
        b_r = await session.execute(
            select(BroadcastMessage).where(BroadcastMessage.id == broadcast_id)
        )
        broadcast = b_r.scalar_one_or_none()
        if not broadcast:
            return _redirect("/broadcast", "Broadcast topilmadi", "danger")
        if broadcast.status not in (BroadcastStatus.PENDING, BroadcastStatus.RUNNING):
            return _redirect("/broadcast", "Bu broadcast bekor qilib bo'lmaydi", "warning")
        broadcast.status = BroadcastStatus.CANCELLED
        await session.commit()
    return _redirect("/broadcast", "Broadcast bekor qilindi")

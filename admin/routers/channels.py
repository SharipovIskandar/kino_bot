from typing import Optional

from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from sqlalchemy import select

from admin.responses import render
from bot.database.connection import AsyncSessionFactory
from bot.database.models import AdminAction, MandatoryChannel
from bot.database.crud.channel import (
    get_all_channels, add_channel, remove_channel, get_channel_by_id,
)

router = APIRouter()


def _redirect(url: str, msg: str = "", type_: str = "success") -> RedirectResponse:
    sep = "&" if "?" in url else "?"
    return RedirectResponse(f"{url}{sep}msg={msg}&type={type_}", status_code=302)


@router.get("")
async def channel_list(request: Request):
    async with AsyncSessionFactory() as session:
        channels = await get_all_channels(session)
    return render(request, "channels/list.html", channels=channels)


@router.post("/add")
async def channel_add(
    request: Request,
    channel_id: int = Form(...),
    channel_title: str = Form(...),
    channel_username: str = Form(""),
    invite_link: str = Form(""),
):
    admin = request.state.admin
    async with AsyncSessionFactory() as session:
        existing = await get_channel_by_id(session, channel_id)
        if existing:
            if not existing.is_active:
                existing.is_active = True
                await session.commit()
                return _redirect("/channels", "Kanal qayta faollashtirildi")
            return _redirect("/channels", "Bu kanal allaqachon mavjud", "warning")

        await add_channel(
            session, channel_id, channel_title,
            added_by=int(admin["sub"]),
            channel_username=channel_username or None,
            invite_link=invite_link or None,
        )
        session.add(AdminAction(
            admin_telegram_id=int(admin["sub"]),
            action_type="channel_add",
            target_id=str(channel_id),
            details={"title": channel_title},
        ))
        await session.commit()

    return _redirect("/channels", f"Kanal '{channel_title}' qo'shildi")


@router.post("/{channel_id}/toggle")
async def channel_toggle(request: Request, channel_id: int):
    admin = request.state.admin
    async with AsyncSessionFactory() as session:
        channel = await get_channel_by_id(session, channel_id)
        if not channel:
            return _redirect("/channels", "Kanal topilmadi", "danger")
        channel.is_active = not channel.is_active
        status = "faollashtirildi" if channel.is_active else "o'chirildi"
        session.add(AdminAction(
            admin_telegram_id=int(admin["sub"]),
            action_type="channel_toggle",
            target_id=str(channel_id),
            details={"is_active": channel.is_active},
        ))
        await session.commit()
    return _redirect("/channels", f"Kanal {status}")


@router.post("/{channel_id}/remove")
async def channel_remove(request: Request, channel_id: int):
    admin = request.state.admin
    async with AsyncSessionFactory() as session:
        ok = await remove_channel(session, channel_id)
        if ok:
            session.add(AdminAction(
                admin_telegram_id=int(admin["sub"]),
                action_type="channel_remove",
                target_id=str(channel_id),
            ))
            await session.commit()
    msg = "Kanal o'chirildi" if ok else "Kanal topilmadi"
    return _redirect("/channels", msg, "success" if ok else "danger")


@router.post("/{channel_id}/edit")
async def channel_edit(
    request: Request,
    channel_id: int,
    channel_title: str = Form(...),
    channel_username: str = Form(""),
    invite_link: str = Form(""),
    order: int = Form(0),
):
    admin = request.state.admin
    async with AsyncSessionFactory() as session:
        channel = await get_channel_by_id(session, channel_id)
        if not channel:
            return _redirect("/channels", "Kanal topilmadi", "danger")
        channel.channel_title = channel_title
        channel.channel_username = channel_username or None
        channel.invite_link = invite_link or None
        channel.order = order
        session.add(AdminAction(
            admin_telegram_id=int(admin["sub"]),
            action_type="channel_edit",
            target_id=str(channel_id),
        ))
        await session.commit()
    return _redirect("/channels", "Kanal yangilandi")

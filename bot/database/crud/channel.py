import hashlib
from typing import List, Optional

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import MandatoryChannel


def _join_link_fake_id(invite_link: str) -> int:
    """
    Join request link uchun unikal fake channel_id yaratish.
    Real Telegram kanal IDlari -100XXXXXXXXXX formatida (13+ raqam),
    shu sababli -1 dan -99_999_999 gacha bo'lgan oraliq xavfsiz.
    """
    h = int(hashlib.md5(invite_link.encode()).hexdigest()[:7], 16)
    return -(h % (10 ** 8 - 1) + 1)


async def get_active_channels(session: AsyncSession) -> List[MandatoryChannel]:
    result = await session.execute(
        select(MandatoryChannel)
        .where(MandatoryChannel.is_active == True)
        .order_by(MandatoryChannel.order)
    )
    return list(result.scalars().all())


async def get_channel_by_id(
    session: AsyncSession, channel_id: int
) -> Optional[MandatoryChannel]:
    result = await session.execute(
        select(MandatoryChannel).where(MandatoryChannel.channel_id == channel_id)
    )
    return result.scalar_one_or_none()


async def get_channel_by_db_id(
    session: AsyncSession, db_id: int
) -> Optional[MandatoryChannel]:
    """PK (id) bo'yicha topish — toggle/delete uchun"""
    result = await session.execute(
        select(MandatoryChannel).where(MandatoryChannel.id == db_id)
    )
    return result.scalar_one_or_none()


async def add_channel(
    session: AsyncSession,
    channel_title: str,
    added_by: int,
    channel_id: Optional[int] = None,
    channel_username: Optional[str] = None,
    invite_link: Optional[str] = None,
) -> MandatoryChannel:
    """
    Majburiy kanal qo'shish yoki qayta faollashtirish.
    channel_id yo'q bo'lsa invite_link'dan fake ID generatsiya qilinadi.
    """
    if channel_id is None:
        channel_id = _join_link_fake_id(invite_link or channel_title)

    result = await session.execute(
        select(MandatoryChannel).where(MandatoryChannel.channel_id == channel_id)
    )
    channel = result.scalar_one_or_none()

    if channel:
        channel.channel_title = channel_title
        channel.channel_username = channel_username
        channel.invite_link = invite_link
        channel.is_active = True
        channel.added_by = added_by
    else:
        order_result = await session.execute(
            select(MandatoryChannel.order).order_by(MandatoryChannel.order.desc()).limit(1)
        )
        last_order = order_result.scalar_one_or_none() or 0

        channel = MandatoryChannel(
            channel_id=channel_id,
            channel_title=channel_title,
            channel_username=channel_username,
            invite_link=invite_link,
            added_by=added_by,
            order=last_order + 1,
        )
        session.add(channel)

    await session.flush()
    await session.refresh(channel)
    return channel


async def delete_channel(session: AsyncSession, db_id: int) -> bool:
    """Kanalni DB'dan butunlay o'chirish (hard delete)"""
    result = await session.execute(
        select(MandatoryChannel).where(MandatoryChannel.id == db_id)
    )
    channel = result.scalar_one_or_none()
    if not channel:
        return False
    await session.delete(channel)
    await session.flush()
    return True


async def toggle_channel(session: AsyncSession, db_id: int) -> Optional[bool]:
    """is_active ni almashtirish. Returns yangi holat yoki None agar topilmasa"""
    result = await session.execute(
        select(MandatoryChannel).where(MandatoryChannel.id == db_id)
    )
    channel = result.scalar_one_or_none()
    if not channel:
        return None
    channel.is_active = not channel.is_active
    await session.flush()
    return channel.is_active


async def get_all_channels(session: AsyncSession) -> List[MandatoryChannel]:
    result = await session.execute(
        select(MandatoryChannel).order_by(MandatoryChannel.order)
    )
    return list(result.scalars().all())

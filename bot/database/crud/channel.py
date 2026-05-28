from typing import List, Optional

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import MandatoryChannel


async def get_active_channels(session: AsyncSession) -> List[MandatoryChannel]:
    """Barcha aktiv majburiy kanallar (tartib bo'yicha)"""
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


async def add_channel(
    session: AsyncSession,
    channel_id: int,
    channel_title: str,
    added_by: int,
    channel_username: Optional[str] = None,
    invite_link: Optional[str] = None,
) -> MandatoryChannel:
    """Majburiy kanal qo'shish yoki qayta faollashtirish"""
    result = await session.execute(
        select(MandatoryChannel).where(MandatoryChannel.channel_id == channel_id)
    )
    channel = result.scalar_one_or_none()

    if channel:
        # Mavjud (noaktiv) kanalni yangilash va faollashtirish
        channel.channel_title = channel_title
        channel.channel_username = channel_username
        channel.invite_link = invite_link
        channel.is_active = True
        channel.added_by = added_by
    else:
        # Oxirgi order raqamini topish
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


async def remove_channel(session: AsyncSession, channel_id: int) -> bool:
    """Majburiy kanalni o'chirish. Returns True agar topilsa"""
    result = await session.execute(
        select(MandatoryChannel).where(MandatoryChannel.channel_id == channel_id)
    )
    channel = result.scalar_one_or_none()
    if not channel:
        return False
    channel.is_active = False
    await session.flush()
    return True


async def get_all_channels(session: AsyncSession) -> List[MandatoryChannel]:
    """Admin uchun: barcha kanallar (noaktivlar ham)"""
    result = await session.execute(
        select(MandatoryChannel).order_by(MandatoryChannel.order)
    )
    return list(result.scalars().all())

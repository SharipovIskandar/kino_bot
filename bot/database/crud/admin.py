from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from bot.database.models import Admin, AdminRole, User


async def get_admin_by_telegram_id(
    session: AsyncSession, telegram_id: int
) -> Optional[Admin]:
    """Telegram ID bo'yicha adminni topish"""
    result = await session.execute(
        select(Admin)
        .join(Admin.user)
        .where(User.telegram_id == telegram_id)
        .options(joinedload(Admin.user))
    )
    return result.scalar_one_or_none()


async def get_all_admins(session: AsyncSession) -> List[Admin]:
    """Barcha adminlar ro'yxati"""
    result = await session.execute(
        select(Admin).options(joinedload(Admin.user))
    )
    return list(result.scalars().all())


async def add_admin(
    session: AsyncSession,
    user: User,
    role: AdminRole,
    added_by: int,
) -> Admin:
    """Yangi admin qo'shish"""
    admin = Admin(
        user_id=user.id,
        role=role,
        added_by=added_by,
    )
    session.add(admin)
    await session.commit()
    await session.refresh(admin)
    return admin


async def remove_admin(
    session: AsyncSession, telegram_id: int
) -> bool:
    """Adminni o'chirish. Returns True agar topilsa"""
    admin = await get_admin_by_telegram_id(session, telegram_id)
    if not admin:
        return False
    await session.delete(admin)
    await session.commit()
    return True


async def is_admin(session: AsyncSession, telegram_id: int) -> bool:
    """Foydalanuvchi admin ekanligini tekshirish"""
    admin = await get_admin_by_telegram_id(session, telegram_id)
    return admin is not None


async def update_admin_role(
    session: AsyncSession,
    telegram_id: int,
    new_role: AdminRole,
) -> bool:
    """Admin rolini o'zgartirish"""
    admin = await get_admin_by_telegram_id(session, telegram_id)
    if not admin:
        return False
    admin.role = new_role
    await session.commit()
    return True

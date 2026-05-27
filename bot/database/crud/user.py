from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from bot.database.models import User, Language


async def get_user(session: AsyncSession, telegram_id: int) -> Optional[User]:
    """Telegram ID bo'yicha userni topish (admin_profile bilan birga)"""
    result = await session.execute(
        select(User)
        .options(selectinload(User.admin_profile))
        .where(User.telegram_id == telegram_id)
    )
    return result.scalar_one_or_none()


async def get_or_create_user(
    session: AsyncSession,
    telegram_id: int,
    full_name: str,
    username: Optional[str] = None,
    language: str = "uz",
) -> tuple[User, bool]:
    """
    Userni olish yoki yaratish.
    Returns: (user, created) — created=True yangi user bo'lsa
    """
    user = await get_user(session, telegram_id)
    if user:
        # Mavjud userni yangilash
        user.full_name = full_name
        user.username = username
        user.last_active_at = datetime.now(timezone.utc)
        await session.commit()
        return user, False

    # Yangi user yaratish
    # Til kodi kichik harfda bo'lishi kerak va qo'llab-quvvatlanishi shart
    supported = {"uz", "ru", "en"}
    lang_code = (language or "uz").lower()
    if lang_code not in supported:
        lang_code = "uz"  # noto'g'ri til kodi bo'lsa default

    user = User(
        telegram_id=telegram_id,
        full_name=full_name,
        username=username,
        language=Language(lang_code),
    )
    session.add(user)
    await session.commit()
    # Yangi userni admin_profile bilan birga refresh qilamiz
    await session.refresh(user, ["admin_profile"])
    return user, True


async def update_user_language(
    session: AsyncSession, telegram_id: int, language: str
) -> None:
    """Foydalanuvchi tilini yangilash"""
    await session.execute(
        update(User)
        .where(User.telegram_id == telegram_id)
        .values(language=Language(language))
    )
    await session.commit()


async def update_last_active(session: AsyncSession, telegram_id: int) -> None:
    """Oxirgi faollik vaqtini yangilash"""
    await session.execute(
        update(User)
        .where(User.telegram_id == telegram_id)
        .values(last_active_at=datetime.now(timezone.utc))
    )
    await session.commit()


async def ban_user(
    session: AsyncSession,
    telegram_id: int,
    reason: str,
    banned_by: int,
) -> bool:
    """Userni ban qilish. Returns True agar user topilsa"""
    user = await get_user(session, telegram_id)
    if not user:
        return False
    user.is_banned = True
    user.ban_reason = reason
    user.banned_at = datetime.now(timezone.utc)
    user.banned_by = banned_by
    await session.commit()
    return True


async def unban_user(session: AsyncSession, telegram_id: int) -> bool:
    """Userdan ban olish. Returns True agar user topilsa"""
    user = await get_user(session, telegram_id)
    if not user:
        return False
    user.is_banned = False
    user.ban_reason = None
    user.banned_at = None
    user.banned_by = None
    await session.commit()
    return True


async def get_user_language(
    session: AsyncSession, telegram_id: int, default: str = "uz"
) -> str:
    """Foydalanuvchi tilini olish"""
    user = await get_user(session, telegram_id)
    if user:
        return user.language.value
    return default

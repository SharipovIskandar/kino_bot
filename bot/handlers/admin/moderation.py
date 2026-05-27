from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import settings
from bot.database.crud.user import get_user, ban_user, unban_user
from bot.database.models import User
from bot.handlers.admin.panel import is_admin
from bot.keyboards.admin_kb import build_back_to_panel_keyboard
from bot.services.i18n import get_text

router = Router(name="admin_moderation")


class ModerationState(StatesGroup):
    waiting_ban = State()
    waiting_unban = State()
    waiting_user_info = State()


def _format_user_info(user: User, lang: str) -> str:
    """User ma'lumotini formatlash"""
    from datetime import timezone
    registered = user.registered_at.strftime("%d.%m.%Y %H:%M") if user.registered_at else "?"
    last_active = user.last_active_at.strftime("%d.%m.%Y %H:%M") if user.last_active_at else "?"

    return get_text(
        "user-info", lang,
        telegram_id=user.telegram_id,
        name=user.full_name,
        username=f"@{user.username}" if user.username else "—",
        language=user.language.value if user.language else "—",
        registered=registered,
        last_active=last_active,
        is_banned="✅ Ha" if user.is_banned else "❌ Yo'q",
        ban_reason=user.ban_reason or "",
    )


# ── Ban qilish ────────────────────────────────────────────────────────────────

@router.message(F.text.startswith("/ban"))
async def cmd_ban_start(
    message: Message,
    db_user: User,
    lang: str,
    state: FSMContext,
) -> None:
    """Ban qilish buyrug'i"""
    if not is_admin(message.from_user.id, db_user):
        await message.answer(get_text("access-denied", lang))
        return

    # /ban 123456789 Spam — inline format
    parts = message.text.split(maxsplit=2)
    if len(parts) >= 2:
        try:
            target_id = int(parts[1])
            reason = parts[2] if len(parts) > 2 else "Sabab ko'rsatilmagan"
            await _do_ban(message, target_id, reason, lang)
            return
        except ValueError:
            pass

    # Forma orqali kiritish
    await message.answer(get_text("ban-prompt", lang))
    await state.set_state(ModerationState.waiting_ban)


@router.message(ModerationState.waiting_ban)
async def process_ban(
    message: Message,
    session: AsyncSession,
    lang: str,
    state: FSMContext,
) -> None:
    """Ban formasi: ID | Sabab"""
    await state.clear()

    text = message.text.strip()
    if "|" in text:
        parts = text.split("|", 1)
        try:
            target_id = int(parts[0].strip())
            reason = parts[1].strip() if len(parts) > 1 else "Sabab ko'rsatilmagan"
        except ValueError:
            await message.answer("❌ Noto'g'ri format. Namuna: <code>123456789 | Spam</code>")
            return
    else:
        try:
            target_id = int(text)
            reason = "Sabab ko'rsatilmagan"
        except ValueError:
            await message.answer("❌ Noto'g'ri format.")
            return

    await _do_ban(message, target_id, reason, lang, session)


async def _do_ban(
    message: Message,
    target_id: int,
    reason: str,
    lang: str,
    session: AsyncSession = None,
) -> None:
    """Ban logikasi"""
    if session is None:
        return

    # Super adminni ban qila olmaymiz
    if target_id in settings.super_admin_list:
        await message.answer("🚫 Super adminni ban qilib bo'lmaydi!")
        return

    user = await get_user(session, target_id)
    if not user:
        await message.answer(get_text("user-not-found", lang))
        return

    success = await ban_user(
        session=session,
        telegram_id=target_id,
        reason=reason,
        banned_by=message.from_user.id,
    )

    if success:
        await message.answer(
            get_text("ban-success", lang, name=user.full_name, reason=reason)
        )
    else:
        await message.answer(get_text("user-not-found", lang))


# ── Unban qilish ──────────────────────────────────────────────────────────────

@router.message(F.text.startswith("/unban"))
async def cmd_unban_start(
    message: Message,
    db_user: User,
    lang: str,
    state: FSMContext,
) -> None:
    """Unban buyrug'i"""
    if not is_admin(message.from_user.id, db_user):
        await message.answer(get_text("access-denied", lang))
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) >= 2:
        try:
            target_id = int(parts[1])
            await _do_unban(message, target_id, lang)
            return
        except ValueError:
            pass

    await message.answer(get_text("unban-prompt", lang))
    await state.set_state(ModerationState.waiting_unban)


@router.message(ModerationState.waiting_unban)
async def process_unban(
    message: Message,
    session: AsyncSession,
    lang: str,
    state: FSMContext,
) -> None:
    await state.clear()
    try:
        target_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Noto'g'ri format. Faqat Telegram ID kiriting.")
        return

    await _do_unban(message, target_id, lang, session)


async def _do_unban(
    message: Message,
    target_id: int,
    lang: str,
    session: AsyncSession = None,
) -> None:
    if session is None:
        return

    user = await get_user(session, target_id)
    if not user:
        await message.answer(get_text("user-not-found", lang))
        return

    if not user.is_banned:
        await message.answer(get_text("unban-not-banned", lang))
        return

    success = await unban_user(session, target_id)
    if success:
        await message.answer(get_text("unban-success", lang, name=user.full_name))


# ── User ma'lumoti ────────────────────────────────────────────────────────────

@router.message(F.text.startswith("/userinfo"))
async def cmd_user_info(
    message: Message,
    session: AsyncSession,
    db_user: User,
    lang: str,
) -> None:
    """User ma'lumotini ko'rish: /userinfo 123456789"""
    if not is_admin(message.from_user.id, db_user):
        await message.answer(get_text("access-denied", lang))
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("ℹ️ Foydalanish: <code>/userinfo [telegram_id]</code>")
        return

    try:
        target_id = int(parts[1].strip())
    except ValueError:
        await message.answer("❌ Noto'g'ri Telegram ID.")
        return

    user = await get_user(session, target_id)
    if not user:
        await message.answer(get_text("user-not-found", lang))
        return

    await message.answer(_format_user_info(user, lang))

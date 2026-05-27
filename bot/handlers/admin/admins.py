from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import settings
from bot.database.crud.admin import (
    get_all_admins, add_admin, remove_admin,
    get_admin_by_telegram_id,
)
from bot.database.crud.user import get_user, get_or_create_user
from bot.database.models import User, AdminRole
from bot.handlers.admin.panel import is_admin
from bot.keyboards.admin_kb import build_back_to_panel_keyboard
from bot.services.i18n import get_text

router = Router(name="admin_admins")


class AdminState(StatesGroup):
    waiting_add_id = State()
    waiting_remove_id = State()


# ── Adminlar ro'yxati ─────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin:admins")
async def callback_admins_list(
    callback: CallbackQuery,
    session: AsyncSession,
    db_user: User,
    lang: str,
) -> None:
    """Adminlar ro'yxatini ko'rsatish"""
    # Faqat super admin ko'ra oladi
    if callback.from_user.id not in settings.super_admin_list:
        await callback.answer(get_text("access-denied", lang), show_alert=True)
        return

    admins = await get_all_admins(session)
    keyboard = _build_admins_keyboard(admins, lang)

    text = get_text("admins-list", lang) + "\n\n"
    if not admins:
        text += "📭 Hali admin yo'q."
    else:
        for i, admin in enumerate(admins, 1):
            role_emoji = "👑" if admin.role == AdminRole.SUPER_ADMIN else "👮" if admin.role == AdminRole.ADMIN else "🛡"
            name = admin.user.full_name if admin.user else "?"
            tg_id = admin.user.telegram_id if admin.user else "?"
            text += f"{i}. {role_emoji} <b>{name}</b> [<code>{tg_id}</code>] — {admin.role.value}\n"

    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


def _build_admins_keyboard(admins: list, lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for admin in admins:
        tg_id = admin.user.telegram_id if admin.user else 0
        builder.row(
            InlineKeyboardButton(
                text=f"🗑 {admin.user.full_name if admin.user else '?'}",
                callback_data=f"admin:remove_admin:{tg_id}",
            )
        )
    builder.row(
        InlineKeyboardButton(
            text="➕ Admin qo'shish",
            callback_data="admin:add_admin",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=get_text("btn-back", lang),
            callback_data="admin:panel",
        )
    )
    return builder.as_markup()


# ── Admin qo'shish ────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin:add_admin")
async def callback_add_admin(
    callback: CallbackQuery,
    db_user: User,
    lang: str,
    state: FSMContext,
) -> None:
    if callback.from_user.id not in settings.super_admin_list:
        await callback.answer(get_text("access-denied", lang), show_alert=True)
        return

    await callback.message.answer(get_text("admin-add-prompt", lang))
    await state.set_state(AdminState.waiting_add_id)
    await callback.answer()


@router.message(AdminState.waiting_add_id)
async def process_add_admin(
    message: Message,
    session: AsyncSession,
    lang: str,
    state: FSMContext,
) -> None:
    """Yangi admin Telegram ID sini qayta ishlash"""
    await state.clear()
    text = message.text.strip()

    try:
        target_id = int(text)
    except ValueError:
        await message.answer("❌ Noto'g'ri format. Faqat raqam (Telegram ID) kiriting.")
        return

    # Super adminni admin qilishga harakat qilish
    if target_id in settings.super_admin_list:
        await message.answer("⚠️ Bu foydalanuvchi allaqachon super admin.")
        return

    # Mavjud adminni tekshirish
    existing = await get_admin_by_telegram_id(session, target_id)
    if existing:
        await message.answer(get_text("admin-already-exists", lang))
        return

    # Userni DB'da topish yoki yaratish
    user = await get_user(session, target_id)
    if not user:
        await message.answer(get_text("user-not-found", lang))
        return

    # Admin qilish
    await add_admin(
        session=session,
        user=user,
        role=AdminRole.ADMIN,
        added_by=message.from_user.id,
    )

    await message.answer(get_text("admin-added", lang, name=user.full_name))


# ── Admin o'chirish ────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("admin:remove_admin:"))
async def callback_remove_admin(
    callback: CallbackQuery,
    session: AsyncSession,
    db_user: User,
    lang: str,
) -> None:
    if callback.from_user.id not in settings.super_admin_list:
        await callback.answer(get_text("access-denied", lang), show_alert=True)
        return

    target_id = int(callback.data.split(":")[2])

    # Super adminni o'chirishga harakat
    if target_id in settings.super_admin_list:
        await callback.answer(get_text("admin-cannot-remove-super", lang), show_alert=True)
        return

    removed = await remove_admin(session, target_id)

    if removed:
        await callback.answer(get_text("admin-removed", lang))
        # Ro'yxatni yangilash
        admins = await get_all_admins(session)
        keyboard = _build_admins_keyboard(admins, lang)

        text = get_text("admins-list", lang) + "\n\n"
        for i, admin in enumerate(admins, 1):
            role_emoji = "👑" if admin.role == AdminRole.ADMIN else "🛡"
            name = admin.user.full_name if admin.user else "?"
            tg_id = admin.user.telegram_id if admin.user else "?"
            text += f"{i}. {role_emoji} <b>{name}</b> [<code>{tg_id}</code>]\n"

        await callback.message.edit_text(text, reply_markup=keyboard)
    else:
        await callback.answer(get_text("admin-not-found", lang), show_alert=True)

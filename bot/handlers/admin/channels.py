import re

from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import User
from bot.database.crud.channel import (
    get_all_channels, add_channel, delete_channel, toggle_channel,
    get_channel_by_id, get_channel_by_db_id,
)
from bot.handlers.admin.panel import is_admin
from bot.keyboards.admin_kb import build_channels_list_keyboard
from bot.services.i18n import get_text
from bot.services.subscription_checker import check_bot_is_admin

router = Router(name="admin_channels")

_JOIN_LINK_RE = re.compile(r"(?:https?://)?t\.me/\+(\S+)", re.IGNORECASE)


def _is_join_link(text: str) -> bool:
    return bool(_JOIN_LINK_RE.search(text))


def _normalize_join_link(text: str) -> str:
    m = _JOIN_LINK_RE.search(text)
    return f"https://t.me/+{m.group(1)}" if m else text


class ChannelState(StatesGroup):
    waiting_channel = State()
    waiting_join_title = State()   # join request link uchun faqat title


# ── Kanallar ro'yxati ────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin:channels")
async def callback_channels_list(
    callback: CallbackQuery,
    session: AsyncSession,
    db_user: User,
    lang: str,
) -> None:
    if not is_admin(callback.from_user.id, db_user):
        await callback.answer(get_text("access-denied", lang), show_alert=True)
        return

    channels = await get_all_channels(session)
    keyboard = build_channels_list_keyboard(channels, lang)
    try:
        await callback.message.edit_text(get_text("channels-list", lang), reply_markup=keyboard)
    except TelegramBadRequest:
        pass
    await callback.answer()


# ── Kanal qo'shish ───────────────────────────────────────────────────────────

@router.callback_query(F.data == "channel:add")
async def callback_channel_add(
    callback: CallbackQuery,
    db_user: User,
    lang: str,
    state: FSMContext,
) -> None:
    if not is_admin(callback.from_user.id, db_user):
        await callback.answer(get_text("access-denied", lang), show_alert=True)
        return

    await callback.message.answer(get_text("channel-add-prompt", lang))
    await state.set_state(ChannelState.waiting_channel)
    await callback.answer()


@router.message(ChannelState.waiting_channel)
async def process_channel_add(
    message: Message,
    session: AsyncSession,
    db_user: User,
    lang: str,
    state: FSMContext,
    bot,
) -> None:
    await state.clear()
    text = (message.text or "").strip()

    # ── Join request link (t.me/+XXXX) ───────────────────────────────────
    if _is_join_link(text):
        invite_link = _normalize_join_link(text)

        # Bot kanalda admin bo'lsa — avtomatik qo'shamiz
        try:
            chat = await bot.get_chat(invite_link)
            channel_id = chat.id
            title = chat.title or str(channel_id)
            username = getattr(chat, "username", None)

            existing = await get_channel_by_id(session, channel_id)
            if existing and existing.is_active:
                await message.answer(get_text("channel-already-exists", lang))
                return

            await add_channel(
                session=session,
                channel_id=channel_id,
                channel_title=title,
                channel_username=username,
                invite_link=invite_link,
                added_by=message.from_user.id,
            )
            await message.answer(get_text("channel-added", lang, title=title))
            return
        except (TelegramForbiddenError, TelegramBadRequest, Exception):
            pass

        # Bot kanalda admin emas → faqat kanal nomini so'raymiz
        await state.set_state(ChannelState.waiting_join_title)
        await state.update_data(join_link=invite_link)
        await message.answer(get_text("channel-join-ask-title", lang))
        return

    # ── Oddiy kanal: @username yoki ID ───────────────────────────────────
    try:
        if text.startswith("-") or text.lstrip("-").isdigit():
            channel_id = int(text)
        else:
            chat = await bot.get_chat(f"@{text.lstrip('@')}")
            channel_id = chat.id
    except Exception:
        await message.answer(get_text("channel-not-found", lang))
        return

    existing = await get_channel_by_id(session, channel_id)
    if existing and existing.is_active:
        await message.answer(get_text("channel-already-exists", lang))
        return

    if not await check_bot_is_admin(bot, channel_id):
        await message.answer(get_text("channel-bot-not-admin", lang))
        return

    try:
        chat = await bot.get_chat(channel_id)
        title = chat.title or str(channel_id)
        username = getattr(chat, "username", None)
        invite_link = getattr(chat, "invite_link", None)
        if not invite_link and not username:
            try:
                invite_link = await bot.export_chat_invite_link(channel_id)
            except Exception:
                pass
    except Exception:
        await message.answer(get_text("channel-not-found", lang))
        return

    await add_channel(
        session=session,
        channel_id=channel_id,
        channel_title=title,
        channel_username=username,
        invite_link=invite_link,
        added_by=message.from_user.id,
    )
    await message.answer(get_text("channel-added", lang, title=title))


@router.message(ChannelState.waiting_join_title)
async def process_join_title(
    message: Message,
    session: AsyncSession,
    lang: str,
    state: FSMContext,
) -> None:
    """Join request link uchun faqat kanal nomini olamiz"""
    data = await state.get_data()
    await state.clear()

    invite_link = data.get("join_link", "")
    title = (message.text or "").strip()

    if not title:
        await message.answer(get_text("channel-join-ask-title", lang))
        return

    # channel_id yo'q — CRUD fake ID generatsiya qiladi
    await add_channel(
        session=session,
        channel_title=title,
        channel_username=None,
        invite_link=invite_link,
        added_by=message.from_user.id,
    )
    await message.answer(get_text("channel-added", lang, title=title))


# ── Kanal ma'lumoti ──────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("channel:info:"))
async def callback_channel_info(
    callback: CallbackQuery,
    session: AsyncSession,
    db_user: User,
    lang: str,
) -> None:
    if not is_admin(callback.from_user.id, db_user):
        await callback.answer(get_text("access-denied", lang), show_alert=True)
        return

    db_id = int(callback.data.split(":")[2])
    ch = await get_channel_by_db_id(session, db_id)

    if not ch:
        await callback.answer(get_text("channel-not-found", lang), show_alert=True)
        return

    await _show_channel_info(callback, ch, lang)


async def _show_channel_info(callback: CallbackQuery, ch, lang: str) -> None:
    status = "✅ Aktiv" if ch.is_active else "❌ Noaktiv"
    link_line = ""
    if ch.invite_link:
        link_line = f"\n🔗 {ch.invite_link}"
    elif ch.channel_username:
        link_line = f"\n🔗 @{ch.channel_username}"

    text = (
        f"📢 <b>{ch.channel_title}</b>\n"
        f"📊 Holat: {status}"
        f"{link_line}"
    )

    toggle_label = "⏸ Noaktiv qilish" if ch.is_active else "▶️ Faollashtirish"
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text=toggle_label,
        callback_data=f"channel:toggle:{ch.id}",
    ))
    builder.row(InlineKeyboardButton(
        text="🗑 O'chirish (butunlay)",
        callback_data=f"channel:delete:{ch.id}",
    ))
    builder.row(InlineKeyboardButton(
        text="◀️ Ortga",
        callback_data="admin:channels",
    ))

    try:
        await callback.message.edit_text(text, reply_markup=builder.as_markup())
    except TelegramBadRequest:
        pass
    await callback.answer()


# ── Toggle aktiv/noaktiv ─────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("channel:toggle:"))
async def callback_channel_toggle(
    callback: CallbackQuery,
    session: AsyncSession,
    db_user: User,
    lang: str,
) -> None:
    if not is_admin(callback.from_user.id, db_user):
        await callback.answer(get_text("access-denied", lang), show_alert=True)
        return

    db_id = int(callback.data.split(":")[2])
    new_status = await toggle_channel(session, db_id)

    if new_status is None:
        await callback.answer(get_text("channel-not-found", lang), show_alert=True)
        return

    label = "✅ Faollashtirildi" if new_status else "⏸ Noaktiv qilindi"
    await callback.answer(label)

    ch = await get_channel_by_db_id(session, db_id)
    if ch:
        await _show_channel_info(callback, ch, lang)


# ── Butunlay o'chirish ───────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("channel:delete:"))
async def callback_channel_delete(
    callback: CallbackQuery,
    session: AsyncSession,
    db_user: User,
    lang: str,
) -> None:
    if not is_admin(callback.from_user.id, db_user):
        await callback.answer(get_text("access-denied", lang), show_alert=True)
        return

    db_id = int(callback.data.split(":")[2])
    deleted = await delete_channel(session, db_id)

    if deleted:
        await callback.answer(get_text("channel-removed", lang))
        channels = await get_all_channels(session)
        keyboard = build_channels_list_keyboard(channels, lang)
        try:
            await callback.message.edit_text(
                get_text("channels-list", lang), reply_markup=keyboard
            )
        except TelegramBadRequest:
            pass
    else:
        await callback.answer(get_text("channel-not-found", lang), show_alert=True)


# ── Eski remove callback (backward compat) ───────────────────────────────────

@router.callback_query(F.data.startswith("channel:remove:"))
async def callback_channel_remove_legacy(
    callback: CallbackQuery,
    session: AsyncSession,
    db_user: User,
    lang: str,
) -> None:
    """Keyboard'dagi 🗑 tugmasi hali channel_id ishlatmoqda — info sahifasiga yo'naltiramiz"""
    if not is_admin(callback.from_user.id, db_user):
        await callback.answer(get_text("access-denied", lang), show_alert=True)
        return

    channel_id = int(callback.data.split(":")[2])
    ch = await get_channel_by_id(session, channel_id)
    if not ch:
        await callback.answer(get_text("channel-not-found", lang), show_alert=True)
        return

    await _show_channel_info(callback, ch, lang)

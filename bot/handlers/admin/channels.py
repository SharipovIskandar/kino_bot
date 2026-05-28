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
    get_all_channels, add_channel, remove_channel, get_channel_by_id
)
from bot.handlers.admin.panel import is_admin
from bot.keyboards.admin_kb import build_channels_list_keyboard
from bot.services.i18n import get_text
from bot.services.subscription_checker import check_bot_is_admin

router = Router(name="admin_channels")

# t.me/+ yoki https://t.me/+ formatdagi join request / invite link
_JOIN_LINK_RE = re.compile(r"(?:https?://)?t\.me/\+(\S+)", re.IGNORECASE)


def _is_join_link(text: str) -> bool:
    return bool(_JOIN_LINK_RE.search(text))


def _normalize_join_link(text: str) -> str:
    m = _JOIN_LINK_RE.search(text)
    if m:
        return f"https://t.me/+{m.group(1)}"
    return text


class ChannelState(StatesGroup):
    waiting_channel = State()
    waiting_join_link_info = State()   # join request link uchun qo'shimcha ma'lumot


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
    text = get_text("channels-list", lang)
    keyboard = build_channels_list_keyboard(channels, lang)
    await callback.message.edit_text(text, reply_markup=keyboard)
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

    # ── Join request / invite link (t.me/+XXXX) ──────────────────────────
    if _is_join_link(text):
        invite_link = _normalize_join_link(text)

        # Bot kanalda admin bo'lsa — ma'lumotlarni avtomatik olamiz
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

        # Bot kanalda admin emas — qo'shimcha ma'lumot so'raymiz
        await state.set_state(ChannelState.waiting_join_link_info)
        await state.update_data(join_link=invite_link)
        await message.answer(get_text("channel-join-link-need-info", lang))
        return

    # ── Oddiy kanal: username yoki ID ────────────────────────────────────
    try:
        if text.startswith("-") or text.lstrip("-").isdigit():
            channel_id = int(text)
        else:
            username = text.lstrip("@")
            chat = await bot.get_chat(f"@{username}")
            channel_id = chat.id
    except Exception:
        await message.answer(get_text("channel-not-found", lang))
        return

    existing = await get_channel_by_id(session, channel_id)
    if existing and existing.is_active:
        await message.answer(get_text("channel-already-exists", lang))
        return

    bot_is_admin = await check_bot_is_admin(bot, channel_id)
    if not bot_is_admin:
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


# ── Join request link: qo'shimcha ma'lumot olish ────────────────────────────

@router.message(ChannelState.waiting_join_link_info)
async def process_join_link_info(
    message: Message,
    session: AsyncSession,
    db_user: User,
    lang: str,
    state: FSMContext,
    bot,
) -> None:
    """
    Join request link uchun kanal ID va nomini olish.
    2 usul qabul qilinadi:
    1. Kanaldan forward qilingan xabar — ID va nom avtomatik olinadi
    2. Matn: "Kanal nomi | -100XXXXXXXXX"
    """
    data = await state.get_data()
    invite_link = data.get("join_link", "")

    # ── Usul 1: Forward qilingan xabar ───────────────────────────────────
    if message.forward_from_chat:
        fwd_chat = message.forward_from_chat
        if fwd_chat.type not in ("channel", "supergroup"):
            await message.answer(get_text("channel-forward-not-channel", lang))
            return

        channel_id = fwd_chat.id
        title = fwd_chat.title or str(channel_id)
        username = getattr(fwd_chat, "username", None)

        await state.clear()

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

    # ── Usul 2: Matn "Kanal nomi | -100XXXXXXXXX" ────────────────────────
    text = (message.text or "").strip()
    if "|" not in text:
        await message.answer(get_text("channel-join-link-format-hint", lang))
        return

    parts = text.split("|", 1)
    title = parts[0].strip()
    try:
        channel_id = int(parts[1].strip())
    except ValueError:
        await message.answer(get_text("channel-join-link-format-hint", lang))
        return

    await state.clear()

    existing = await get_channel_by_id(session, channel_id)
    if existing and existing.is_active:
        await message.answer(get_text("channel-already-exists", lang))
        return

    await add_channel(
        session=session,
        channel_id=channel_id,
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

    channel_id = int(callback.data.split(":")[2])
    ch = await get_channel_by_id(session, channel_id)

    if not ch:
        await callback.answer(get_text("channel-not-found", lang), show_alert=True)
        return

    status = "✅ Aktiv" if ch.is_active else "❌ Noaktiv"
    link_line = ""
    if ch.invite_link:
        link_line = f"\n🔗 Link: {ch.invite_link}"
    elif ch.channel_username:
        link_line = f"\n🔗 @{ch.channel_username}"

    text = (
        f"📢 <b>{ch.channel_title}</b>\n"
        f"🆔 ID: <code>{ch.channel_id}</code>\n"
        f"📊 Holat: {status}"
        f"{link_line}"
    )

    builder = InlineKeyboardBuilder()
    if ch.is_active:
        builder.row(InlineKeyboardButton(
            text="🗑 Ro'yxatdan o'chirish",
            callback_data=f"channel:remove:{ch.channel_id}",
        ))
    builder.row(InlineKeyboardButton(
        text=get_text("btn-back", lang),
        callback_data="admin:channels",
    ))

    try:
        await callback.message.edit_text(text, reply_markup=builder.as_markup())
    except TelegramBadRequest:
        pass
    await callback.answer()


# ── Kanalni o'chirish ────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("channel:remove:"))
async def callback_channel_remove(
    callback: CallbackQuery,
    session: AsyncSession,
    db_user: User,
    lang: str,
) -> None:
    if not is_admin(callback.from_user.id, db_user):
        await callback.answer(get_text("access-denied", lang), show_alert=True)
        return

    channel_id = int(callback.data.split(":")[2])
    removed = await remove_channel(session, channel_id)

    if removed:
        await callback.answer(get_text("channel-removed", lang))
        channels = await get_all_channels(session)
        text = get_text("channels-list", lang)
        keyboard = build_channels_list_keyboard(channels, lang)
        try:
            await callback.message.edit_text(text, reply_markup=keyboard)
        except TelegramBadRequest:
            pass
    else:
        await callback.answer(get_text("channel-not-found", lang), show_alert=True)

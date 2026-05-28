import re

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import User
from bot.database.crud.channel import (
    get_all_channels, add_channel, remove_channel, get_channel_by_id
)
from bot.handlers.admin.panel import is_admin
from bot.keyboards.admin_kb import build_channels_list_keyboard, build_back_to_panel_keyboard
from bot.services.i18n import get_text
from bot.services.subscription_checker import check_bot_is_admin

router = Router(name="admin_channels")

# t.me/+ yoki https://t.me/+ formatdagi join request/invite link
_JOIN_LINK_RE = re.compile(r"(?:https?://)?t\.me/\+(\S+)", re.IGNORECASE)


def _is_join_link(text: str) -> bool:
    return bool(_JOIN_LINK_RE.search(text))


def _normalize_join_link(text: str) -> str:
    """Linkni standart https://t.me/+XXX formatga keltirish"""
    m = _JOIN_LINK_RE.search(text)
    if m:
        return f"https://t.me/+{m.group(1)}"
    return text


class ChannelState(StatesGroup):
    waiting_channel = State()
    waiting_join_link_title = State()


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
    text = message.text.strip() if message.text else ""

    # ── Join request / invite link (t.me/+XXXX) ──────────────────────────
    if _is_join_link(text):
        invite_link = _normalize_join_link(text)

        # Bot orqali kanal ma'lumotlarini olishga urinish (bot kanalda admin bo'lsa ishlaydi)
        try:
            chat = await bot.get_chat(invite_link)
            channel_id = chat.id
            title = chat.title or str(channel_id)
            username = chat.username

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

        except Exception:
            # Bot kanalda emas yoki link noto'g'ri — title so'raymiz
            await state.set_state(ChannelState.waiting_join_link_title)
            await state.update_data(join_link=invite_link)
            await message.answer(get_text("channel-join-link-title-prompt", lang))
        return

    # ── Username yoki ID ──────────────────────────────────────────────────
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


@router.message(ChannelState.waiting_join_link_title)
async def process_join_link_title(
    message: Message,
    session: AsyncSession,
    db_user: User,
    lang: str,
    state: FSMContext,
) -> None:
    """Join request link uchun kanal nomi + ID so'ralganda"""
    data = await state.get_data()
    await state.clear()

    invite_link = data.get("join_link", "")
    text = message.text.strip() if message.text else ""

    # Format: "Kanal nomi | -100XXXXXXXXX"
    if "|" in text:
        parts = text.split("|", 1)
        title = parts[0].strip()
        try:
            channel_id = int(parts[1].strip())
        except ValueError:
            await message.answer(get_text("channel-not-found", lang))
            return
    else:
        await message.answer(get_text("channel-join-link-format-hint", lang))
        return

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


@router.callback_query(F.data.startswith("channel:info:"))
async def callback_channel_info(
    callback: CallbackQuery,
    session: AsyncSession,
    db_user: User,
    lang: str,
) -> None:
    """Kanal ma'lumotini ko'rsatish + o'chirish tugmasi"""
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

    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()


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
        await callback.message.edit_text(text, reply_markup=keyboard)
    else:
        await callback.answer(get_text("channel-not-found", lang), show_alert=True)

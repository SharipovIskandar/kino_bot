from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
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


class ChannelState(StatesGroup):
    waiting_channel = State()


@router.callback_query(F.data == "admin:channels")
async def callback_channels_list(
    callback: CallbackQuery,
    session: AsyncSession,
    db_user: User,
    lang: str,
) -> None:
    """Kanallar ro'yxatini ko'rsatish"""
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
    """Kanal qo'shish so'rovi"""
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
    """Kanal username yoki ID ni qayta ishlash"""
    await state.clear()
    text = message.text.strip()

    # Channel ID yoki username aniqlash
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

    # Mavjudligini tekshirish
    existing = await get_channel_by_id(session, channel_id)
    if existing and existing.is_active:
        await message.answer(get_text("channel-already-exists", lang))
        return

    # Bot admin ekanini tekshirish
    bot_is_admin = await check_bot_is_admin(bot, channel_id)
    if not bot_is_admin:
        await message.answer(get_text("channel-bot-not-admin", lang))
        return

    # Kanal ma'lumotlarini olish
    try:
        chat = await bot.get_chat(channel_id)
        title = chat.title or str(channel_id)
        username = chat.username
        invite_link = chat.invite_link
    except Exception:
        await message.answer(get_text("channel-not-found", lang))
        return

    # DB'ga qo'shish
    await add_channel(
        session=session,
        channel_id=channel_id,
        channel_title=title,
        channel_username=username,
        invite_link=invite_link,
        added_by=message.from_user.id,
    )

    await message.answer(get_text("channel-added", lang, title=title))


@router.callback_query(F.data.startswith("channel:remove:"))
async def callback_channel_remove(
    callback: CallbackQuery,
    session: AsyncSession,
    db_user: User,
    lang: str,
) -> None:
    """Kanalni o'chirish"""
    if not is_admin(callback.from_user.id, db_user):
        await callback.answer(get_text("access-denied", lang), show_alert=True)
        return

    channel_id = int(callback.data.split(":")[2])
    removed = await remove_channel(session, channel_id)

    if removed:
        await callback.answer(get_text("channel-removed", lang))
        # Ro'yxatni yangilash
        channels = await get_all_channels(session)
        keyboard = build_channels_list_keyboard(channels, lang)
        await callback.message.edit_reply_markup(reply_markup=keyboard)
    else:
        await callback.answer(get_text("channel-not-found", lang), show_alert=True)

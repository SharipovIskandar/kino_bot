import asyncio
import time
from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import (
    BroadcastMessage, BroadcastTarget, MediaType, User,
)
from bot.handlers.admin.panel import is_admin
from bot.keyboards.admin_kb import (
    build_broadcast_target_keyboard,
    build_broadcast_confirm_keyboard,
    build_back_to_panel_keyboard,
)
from bot.services.broadcaster import get_target_user_ids, run_broadcast
from bot.services.i18n import get_text

router = Router(name="admin_broadcast")

# Broadcast mutex — bir vaqtda bitta broadcast
_broadcast_running = False


class BroadcastState(StatesGroup):
    choosing_target = State()
    waiting_message = State()
    confirming = State()


TARGET_LABELS = {
    "all": "Barcha foydalanuvchilar",
    "active_7d": "Faol (7 kun)",
    "active_30d": "Faol (30 kun)",
    "lang_uz": "🇺🇿 O'zbeklar",
    "lang_ru": "🇷🇺 Ruslar",
    "lang_en": "🇺🇸 Inglizlar",
}

TARGET_MAP = {
    "all": BroadcastTarget.ALL,
    "active_7d": BroadcastTarget.ACTIVE_7D,
    "active_30d": BroadcastTarget.ACTIVE_30D,
    "lang_uz": BroadcastTarget.LANG_UZ,
    "lang_ru": BroadcastTarget.LANG_RU,
    "lang_en": BroadcastTarget.LANG_EN,
}


# ── Broadcast boshlash ────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin:broadcast")
async def callback_broadcast_start(
    callback: CallbackQuery,
    db_user: User,
    lang: str,
    state: FSMContext,
) -> None:
    global _broadcast_running

    if not is_admin(callback.from_user.id, db_user):
        await callback.answer(get_text("access-denied", lang), show_alert=True)
        return

    if _broadcast_running:
        await callback.answer("⏳ Hozir broadcast ishlayapti, kuting...", show_alert=True)
        return

    await callback.message.edit_text(
        get_text("broadcast-choose-target", lang),
        reply_markup=build_broadcast_target_keyboard(lang),
    )
    await state.set_state(BroadcastState.choosing_target)
    await callback.answer()


# ── Target tanlash ────────────────────────────────────────────────────────────

@router.callback_query(
    BroadcastState.choosing_target,
    F.data.startswith("broadcast:target:")
)
async def callback_broadcast_target(
    callback: CallbackQuery,
    session: AsyncSession,
    lang: str,
    state: FSMContext,
) -> None:
    target_key = callback.data.split(":")[2]  # broadcast:target:all → all

    if target_key not in TARGET_MAP:
        await callback.answer("❌ Noto'g'ri target")
        return

    target = TARGET_MAP[target_key]

    # Oldindan hisoblab qo'yamiz
    user_ids = await get_target_user_ids(session, target)
    count = len(user_ids)

    await state.update_data(
        target_key=target_key,
        target=target.value,
        user_ids=user_ids,
        count=count,
    )

    await callback.message.edit_text(
        get_text("broadcast-send-message", lang)
    )
    await state.set_state(BroadcastState.waiting_message)
    await callback.answer()


# ── Xabar qabul qilish ────────────────────────────────────────────────────────

@router.message(BroadcastState.waiting_message)
async def process_broadcast_message(
    message: Message,
    lang: str,
    state: FSMContext,
) -> None:
    """Broadcast xabarini qabul qilish va preview ko'rsatish"""
    data = await state.get_data()

    # Media type aniqlash
    media_file_id = None
    media_type = None
    text = message.text or message.caption or ""

    if message.photo:
        media_file_id = message.photo[-1].file_id
        media_type = MediaType.PHOTO.value
    elif message.video:
        media_file_id = message.video.file_id
        media_type = MediaType.VIDEO.value
    elif message.document:
        media_file_id = message.document.file_id
        media_type = MediaType.DOCUMENT.value
    elif message.animation:
        media_file_id = message.animation.file_id
        media_type = MediaType.ANIMATION.value

    await state.update_data(
        broadcast_text=text,
        media_file_id=media_file_id,
        media_type=media_type,
        msg_type="media" if media_file_id else "text",
    )

    target_label = TARGET_LABELS.get(data.get("target_key", "all"), "?")
    count = data.get("count", 0)

    preview_text = get_text(
        "broadcast-preview", lang,
        target=target_label,
        count=count,
    )

    await message.answer(
        preview_text,
        reply_markup=build_broadcast_confirm_keyboard(lang),
    )
    await state.set_state(BroadcastState.confirming)


# ── Tasdiqlash ────────────────────────────────────────────────────────────────

@router.callback_query(
    BroadcastState.confirming,
    F.data == "broadcast:confirm:yes"
)
async def callback_broadcast_confirm(
    callback: CallbackQuery,
    session: AsyncSession,
    db_user: User,
    lang: str,
    state: FSMContext,
    bot: Bot,
) -> None:
    global _broadcast_running

    data = await state.get_data()
    await state.clear()

    if _broadcast_running:
        await callback.answer("⏳ Hozir boshqa broadcast ishlayapti!", show_alert=True)
        return

    user_ids: list = data.get("user_ids", [])
    target_raw = data.get("target", BroadcastTarget.ALL.value)
    text = data.get("broadcast_text", "")
    media_file_id = data.get("media_file_id")
    media_type_raw = data.get("media_type")

    if not user_ids:
        await callback.message.edit_text("📭 Maqsad auditoriya bo'sh.")
        return

    # DB'ga saqlash
    broadcast = BroadcastMessage(
        text=text,
        media_file_id=media_file_id,
        media_type=MediaType(media_type_raw) if media_type_raw else MediaType.TEXT,
        target=BroadcastTarget(target_raw),
        created_by=callback.from_user.id,
    )
    session.add(broadcast)
    await session.commit()
    await session.refresh(broadcast)

    total = len(user_ids)
    status_msg = await callback.message.edit_text(
        get_text("broadcast-started", lang, total=total)
    )
    await callback.answer()

    _broadcast_running = True
    start_time = time.time()

    async def progress_update(sent: int, total: int):
        try:
            await status_msg.edit_text(
                get_text("broadcast-progress", lang, sent=sent, total=total)
            )
        except Exception:
            pass

    try:
        result = await run_broadcast(
            bot=bot,
            session=session,
            broadcast=broadcast,
            user_ids=user_ids,
            progress_callback=progress_update,
        )

        duration = round(time.time() - start_time, 1)
        await status_msg.edit_text(
            get_text(
                "broadcast-done", lang,
                sent=result.total_sent,
                failed=result.total_failed,
                duration=duration,
            ),
            reply_markup=build_back_to_panel_keyboard(lang),
        )
    finally:
        _broadcast_running = False


@router.callback_query(
    BroadcastState.confirming,
    F.data == "broadcast:confirm:no"
)
async def callback_broadcast_cancel(
    callback: CallbackQuery,
    lang: str,
    state: FSMContext,
) -> None:
    await state.clear()
    await callback.message.edit_text(
        "❌ Broadcast bekor qilindi.",
        reply_markup=build_back_to_panel_keyboard(lang),
    )
    await callback.answer()

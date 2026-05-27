from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.services.i18n import get_text


def build_admin_panel_keyboard(lang: str = "uz") -> InlineKeyboardMarkup:
    """Admin bosh panel klaviaturasi"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=get_text("btn-admin-movies", lang),
            callback_data="admin:movies",
        ),
        InlineKeyboardButton(
            text=get_text("btn-admin-channels", lang),
            callback_data="admin:channels",
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text=get_text("btn-admin-admins", lang),
            callback_data="admin:admins",
        ),
        InlineKeyboardButton(
            text=get_text("btn-admin-broadcast", lang),
            callback_data="admin:broadcast",
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text=get_text("btn-admin-stats", lang),
            callback_data="admin:stats",
        ),
        InlineKeyboardButton(
            text=get_text("btn-admin-sync", lang),
            callback_data="admin:sync",
        ),
    )
    return builder.as_markup()


def build_broadcast_target_keyboard(lang: str = "uz") -> InlineKeyboardMarkup:
    """Broadcast target tanlash klaviaturasi"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=get_text("btn-target-all", lang),
            callback_data="broadcast:target:all",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=get_text("btn-target-active-7d", lang),
            callback_data="broadcast:target:active_7d",
        ),
        InlineKeyboardButton(
            text=get_text("btn-target-active-30d", lang),
            callback_data="broadcast:target:active_30d",
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text=get_text("btn-target-lang-uz", lang),
            callback_data="broadcast:target:lang_uz",
        ),
        InlineKeyboardButton(
            text=get_text("btn-target-lang-ru", lang),
            callback_data="broadcast:target:lang_ru",
        ),
        InlineKeyboardButton(
            text=get_text("btn-target-lang-en", lang),
            callback_data="broadcast:target:lang_en",
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text=get_text("btn-cancel", lang),
            callback_data="admin:panel",
        )
    )
    return builder.as_markup()


def build_broadcast_confirm_keyboard(lang: str = "uz") -> InlineKeyboardMarkup:
    """Broadcast tasdiqlash klaviaturasi"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=get_text("btn-yes", lang),
            callback_data="broadcast:confirm:yes",
        ),
        InlineKeyboardButton(
            text=get_text("btn-no", lang),
            callback_data="broadcast:confirm:no",
        ),
    )
    return builder.as_markup()


def build_channels_list_keyboard(
    channels: list, lang: str = "uz"
) -> InlineKeyboardMarkup:
    """Kanal ro'yxati + o'chirish tugmalari"""
    builder = InlineKeyboardBuilder()
    for ch in channels:
        status = "✅" if ch.is_active else "❌"
        builder.row(
            InlineKeyboardButton(
                text=f"{status} {ch.channel_title}",
                callback_data=f"channel:info:{ch.channel_id}",
            ),
            InlineKeyboardButton(
                text="🗑",
                callback_data=f"channel:remove:{ch.channel_id}",
            ),
        )
    builder.row(
        InlineKeyboardButton(
            text=get_text("btn-channel-add", lang),
            callback_data="channel:add",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=get_text("btn-back", lang),
            callback_data="admin:panel",
        )
    )
    return builder.as_markup()


def build_back_to_panel_keyboard(lang: str = "uz") -> InlineKeyboardMarkup:
    """Panel'ga qaytish tugmasi"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=get_text("btn-back", lang),
            callback_data="admin:panel",
        )
    )
    return builder.as_markup()

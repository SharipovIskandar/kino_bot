from typing import List

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from bot.database.models import MandatoryChannel
from bot.services.i18n import get_text


def build_language_keyboard() -> InlineKeyboardMarkup:
    """Til tanlash klaviaturasi"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🇺🇿 O'zbek", callback_data="lang_uz"),
        InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru"),
        InlineKeyboardButton(text="🇺🇸 English", callback_data="lang_en"),
    )
    return builder.as_markup()


def build_subscription_keyboard(
    channels: List[MandatoryChannel],
    lang: str = "uz",
) -> InlineKeyboardMarkup:
    """Majburiy kanal obuna tugmalari"""
    builder = InlineKeyboardBuilder()

    for channel in channels:
        # Kanal URL'ini aniqlash
        if channel.invite_link:
            url = channel.invite_link
        elif channel.channel_username:
            url = f"https://t.me/{channel.channel_username.lstrip('@')}"
        else:
            url = f"https://t.me/c/{str(channel.channel_id).lstrip('-100')}"

        builder.row(
            InlineKeyboardButton(
                text=f"📢 {channel.channel_title}",
                url=url,
            )
        )

    # "Tekshirish" tugmasi
    builder.row(
        InlineKeyboardButton(
            text=get_text("check-subscription-btn", lang),
            callback_data="check_sub",
        )
    )
    return builder.as_markup()


def build_main_menu(lang: str = "uz") -> ReplyKeyboardMarkup:
    """Asosiy menyu — reply keyboard"""
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="🔍 " + ("Qidirish" if lang == "uz" else "Поиск" if lang == "ru" else "Search")),
    )
    builder.row(
        KeyboardButton(text="🌐 " + ("Til" if lang == "uz" else "Язык" if lang == "ru" else "Language")),
        KeyboardButton(text="ℹ️ " + ("Yordam" if lang == "uz" else "Помощь" if lang == "ru" else "Help")),
    )
    return builder.as_markup(resize_keyboard=True)


def build_cancel_keyboard(lang: str = "uz") -> ReplyKeyboardMarkup:
    """Bekor qilish klaviaturasi"""
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text=get_text("btn-cancel", lang)))
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


def build_confirm_keyboard(lang: str = "uz") -> InlineKeyboardMarkup:
    """Tasdiqlash inline klaviaturasi"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=get_text("btn-yes", lang), callback_data="confirm_yes"),
        InlineKeyboardButton(text=get_text("btn-no", lang), callback_data="confirm_no"),
    )
    return builder.as_markup()

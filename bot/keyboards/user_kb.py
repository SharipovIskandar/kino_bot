from typing import List

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from bot.database.models import MandatoryChannel
from bot.services.i18n import get_text



def build_subscription_keyboard(
    channels: List[MandatoryChannel],
    lang: str = "uz",
    channel_urls: dict | None = None,
) -> InlineKeyboardMarkup:
    """Majburiy kanal obuna tugmalari"""
    builder = InlineKeyboardBuilder()

    for channel in channels:
        # URL aniqlash: override dict > invite_link > username > None
        if channel_urls and channel.channel_id in channel_urls:
            url = channel_urls[channel.channel_id]
        elif channel.invite_link:
            url = channel.invite_link
        elif channel.channel_username:
            url = f"https://t.me/{channel.channel_username.lstrip('@')}"
        else:
            url = None  # Private channel without any link

        if url:
            builder.row(
                InlineKeyboardButton(
                    text=f"📢 {channel.channel_title}",
                    url=url,
                )
            )
        else:
            # Link yo'q — tugmani ko'rsatmaymiz (faqat kanal nomi)
            # Bu holat admin invite_link o'rnatmagan bo'lganda uchraydi
            pass

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

from aiogram import Router, F
from aiogram.types import Message

from bot.keyboards.user_kb import build_main_menu
from bot.services.i18n import get_text

router = Router(name="fallback")


@router.message(F.text & F.text.startswith("/"))
async def cmd_unknown(message: Message, lang: str) -> None:
    """Noma'lum yoki yo'q buyruq"""
    await message.answer(
        get_text("unknown-command", lang),
        reply_markup=build_main_menu(lang),
    )


@router.message()
async def message_fallback(message: Message, lang: str) -> None:
    """Hech qanday handler ushlmagan har qanday xabar"""
    await message.answer(
        get_text("unknown-message", lang),
        reply_markup=build_main_menu(lang),
    )

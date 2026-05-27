from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.database.models import User
from bot.keyboards.user_kb import build_main_menu
from bot.services.i18n import get_text

router = Router(name="start")

_HELP_BTN = {"ℹ️ Yordam", "ℹ️ Помощь", "ℹ️ Help"}


@router.message(CommandStart())
async def cmd_start(message: Message, db_user: User, lang: str, state: FSMContext) -> None:
    """Bot ishga tushirilganda — to'liq xush kelibsiz xabari"""
    await state.clear()
    await message.answer(
        get_text("welcome", lang, name=message.from_user.full_name),
        reply_markup=build_main_menu(lang),
    )


@router.message(Command("help"))
@router.message(F.text.in_(_HELP_BTN))
async def cmd_help(message: Message, lang: str) -> None:
    """Yordam — /help yoki '❓ Yordam' tugmasi"""
    await message.answer(
        get_text("help", lang),
        reply_markup=build_main_menu(lang),
    )

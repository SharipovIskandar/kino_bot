from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery

from bot.database.models import User
from bot.database.crud.user import update_user_language
from bot.keyboards.user_kb import build_language_keyboard, build_main_menu
from bot.services.i18n import get_text

router = Router(name="start")

# Reply keyboard matni → til kaliti (3 tilda)
_SEARCH_BTN   = {"🔍 Qidirish", "🔍 Поиск", "🔍 Search"}
_LANG_BTN     = {"🌐 Til", "🌐 Язык", "🌐 Language"}
_HELP_BTN     = {"ℹ️ Yordam", "ℹ️ Помощь", "ℹ️ Help"}


@router.message(CommandStart())
async def cmd_start(message: Message, db_user: User, lang: str) -> None:
    """Bot ishga tushirilganda — salomlashish va til tanlash"""
    # db_user doim mavjud (middleware yaratadi), shuning uchun
    # yangi user'ni created flag bilan aniqlaymiz
    # Yangi user: registered_at va last_active_at deyarli bir xil vaqtda

    # Yangi yoki qaytib kelgan user'ni aniqlash uchun session'dagi created flagni ishlatamiz
    # (user_register.py created=True qaytarsa yangi deb hisoblaymiz)
    # Ammo bu yerda faqat lang va db_user bor — shuning uchun welcome ko'rsatamiz

    await message.answer(
        get_text("welcome", lang, name=message.from_user.full_name),
        reply_markup=build_main_menu(lang),
    )

    # Har doim til tanlashni taklif qilamiz /start da
    await message.answer(
        get_text("choose-language", lang),
        reply_markup=build_language_keyboard(),
    )


@router.message(Command("language"))
@router.message(F.text.in_(_LANG_BTN))
async def cmd_language(message: Message, lang: str) -> None:
    """Til tanlash — /language yoki '🌐 Til' tugmasi"""
    await message.answer(
        get_text("choose-language", lang),
        reply_markup=build_language_keyboard(),
    )


@router.callback_query(lambda c: c.data and c.data.startswith("lang_"))
async def process_language_choice(
    callback: CallbackQuery,
    session,
    db_user: User,
    lang: str,
) -> None:
    """Til tanlash callback"""
    chosen_lang = callback.data.split("_")[1]  # lang_uz → uz

    if chosen_lang not in ("uz", "ru", "en"):
        await callback.answer()
        return

    await update_user_language(session, callback.from_user.id, chosen_lang)

    await callback.message.edit_text(
        get_text("language-changed", chosen_lang),
    )
    # Yangi til bilan bosh menyu
    await callback.message.answer(
        get_text("welcome-back", chosen_lang, name=callback.from_user.full_name),
        reply_markup=build_main_menu(chosen_lang),
    )
    await callback.answer("✅")


@router.message(Command("help"))
@router.message(F.text.in_(_HELP_BTN))
async def cmd_help(message: Message, lang: str) -> None:
    """Yordam — /help yoki '❓ Yordam' tugmasi"""
    await message.answer(
        get_text("help", lang),
        reply_markup=build_main_menu(lang),
    )

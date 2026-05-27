from aiogram import Router
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.crud.channel import get_active_channels
from bot.database.models import User
from bot.keyboards.user_kb import build_subscription_keyboard, build_main_menu
from bot.services.subscription_checker import check_user_subscriptions
from bot.services.i18n import get_text

router = Router(name="subscription")


@router.callback_query(lambda c: c.data == "check_sub")
async def process_check_subscription(
    callback: CallbackQuery,
    session: AsyncSession,
    db_user: User,
    lang: str,
    bot,
) -> None:
    """'Obuna bo'ldim, tekshir!' tugmasini bosganida"""
    channels = await get_active_channels(session)

    if not channels:
        # Kanal yo'q — botni ishlata oladi
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer(
            get_text("subscription-ok", lang),
            reply_markup=build_main_menu(lang),
        )
        await callback.answer()
        return

    not_subscribed = await check_user_subscriptions(
        bot=bot,
        user_id=callback.from_user.id,
        channels=channels,
    )

    if not not_subscribed:
        # Hammasi tekshirildi — botni ishlata oladi
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer(
            get_text("subscription-ok", lang),
            reply_markup=build_main_menu(lang),
        )
    else:
        # Hali obuna bo'lmagan kanallar bor
        from bot.middlewares.subscription import _get_invite_links
        channel_urls = await _get_invite_links(bot, not_subscribed, session=session)
        keyboard = build_subscription_keyboard(not_subscribed, lang, channel_urls=channel_urls)
        try:
            await callback.message.edit_reply_markup(reply_markup=keyboard)
        except Exception:
            pass
        await callback.answer(
            get_text("subscription-fail", lang),
            show_alert=True,
        )

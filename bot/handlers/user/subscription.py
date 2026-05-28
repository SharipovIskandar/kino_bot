from aiogram import Router
from aiogram.types import CallbackQuery, Message
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.crud.channel import get_active_channels
from bot.database.models import User
from bot.keyboards.user_kb import build_subscription_keyboard, build_main_menu
from bot.services.subscription_checker import check_user_subscriptions, _is_fake_channel_id
from bot.services.i18n import get_text

router = Router(name="subscription")


@router.callback_query(lambda c: c.data == "check_sub")
async def process_check_subscription(
    callback: CallbackQuery,
    session: AsyncSession,
    db_user: User,
    lang: str,
    bot,
    redis: Redis,
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

    real_not_subscribed = [ch for ch in not_subscribed if not _is_fake_channel_id(ch.channel_id)]
    fake_channels = [ch for ch in not_subscribed if _is_fake_channel_id(ch.channel_id)]

    if not real_not_subscribed:
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer(
            get_text("subscription-ok", lang),
            reply_markup=build_main_menu(lang),
        )
    else:
        # Hali obuna bo'lmagan real kanallar + join-request kanallar
        channels_to_show = real_not_subscribed + fake_channels
        from bot.middlewares.subscription import _get_invite_links
        channel_urls = await _get_invite_links(bot, channels_to_show, session=session)
        keyboard = build_subscription_keyboard(channels_to_show, lang, channel_urls=channel_urls)
        try:
            await callback.message.edit_reply_markup(reply_markup=keyboard)
        except Exception:
            pass
        await callback.answer(
            get_text("subscription-fail", lang),
            show_alert=True,
        )

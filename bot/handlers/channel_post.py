from aiogram import Router, F
from aiogram.types import Message
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import settings
from bot.database.crud.movie import upsert_movie
from bot.database.models import User, Movie, MovieLanguageType
from bot.handlers.admin.panel import is_admin
from bot.services.caption_parser import parse_caption
from bot.services.i18n import get_text

router = Router(name="channel_post")


async def _save_movie_from_message(
    session: AsyncSession,
    caption: str,
    channel_message_id: int,
    photo_file_id: str | None,
    bot=None,
) -> tuple[str, bool] | None:
    """Caption'dan kino parse qilib DB'ga saqlaydi. (code, created) yoki None qaytaradi."""
    parsed = parse_caption(caption, channel_message_id)
    if not parsed:
        logger.debug(
            f"Msg {channel_message_id}: yetarli ma'lumot yo'q, saqlanmadi"
        )
        return None

    # language_type str -> MovieLanguageType enum konvertatsiyasi
    lang_type = None
    if parsed.language_type:
        try:
            lang_type = MovieLanguageType(parsed.language_type)
        except ValueError:
            pass  # Noma'lum qiymat — None qoladi

    _, created = await upsert_movie(
        session=session,
        code=parsed.code,
        channel_message_id=channel_message_id,
        genres=parsed.genres if parsed.genres else None,
        title=parsed.title,
        description=parsed.description,
        year=parsed.year,
        duration=parsed.duration,
        country=parsed.country,
        director=parsed.director,
        cast=parsed.cast,
        imdb_rating=parsed.imdb_rating,
        kinopoisk_rating=parsed.kinopoisk_rating,
        age_rating=parsed.age_rating,
        language_type=lang_type,
        poster_file_id=photo_file_id,
    )

    action = "qo'shildi" if created else "yangilandi"
    logger.info(f"Kino saqlandi: {parsed.title or parsed.code} (#{parsed.code}) — {action}")

    # Admin chatiga bildiruv yuborish
    if bot and settings.super_admin_list:
        title_display = parsed.title or parsed.code
        action_emoji = "✅" if created else "🔄"
        notif_text = (
            f"{action_emoji} <b>Kino {action}:</b> {title_display} "
            f"(#{parsed.code})"
        )
        for admin_id in settings.super_admin_list:
            try:
                await bot.send_message(admin_id, notif_text)
            except Exception:
                pass

    return parsed.code, created


# ── Kanalga yangi post tushganda avtomatik saqlash ────────────────────────────

@router.channel_post(F.chat.id == settings.movie_channel_id)
async def handle_new_channel_post(message: Message, session: AsyncSession) -> None:
    """Kino kanaliga yangi xabar kelganda avtomatik DB'ga yozish."""
    caption = message.caption or message.text
    if not caption:
        return

    photo_file_id = message.photo[-1].file_id if message.photo else None

    result = await _save_movie_from_message(
        session, caption, message.message_id, photo_file_id, bot=message.bot
    )
    if not result:
        logger.debug(
            f"Kanal post {message.message_id}: saqlanmadi (yetarli ma'lumot yo'q yoki kod topilmadi)"
        )


# ── Admin kino kanalidan forward qilganda saqlash ────────────────────────────

@router.message(
    lambda m: (
        m.forward_origin is not None
        and hasattr(m.forward_origin, "chat")
        and m.forward_origin.chat.id == settings.movie_channel_id
    )
)
async def handle_admin_forward(
    message: Message,
    session: AsyncSession,
    db_user: User,
    lang: str,
) -> None:
    """Admin kino kanalidan xabarni botga forward qilganda kino saqlash."""
    if not is_admin(message.from_user.id, db_user):
        return

    channel_message_id = message.forward_origin.message_id
    caption = message.caption or message.text

    if not caption:
        await message.reply(get_text("forward-no-caption", lang))
        return

    photo_file_id = message.photo[-1].file_id if message.photo else None

    # Dublikat tekshiruvi: channel_message_id bo'yicha
    existing = await session.execute(
        select(Movie).where(Movie.channel_message_id == channel_message_id)
    )
    existing_movie = existing.scalar_one_or_none()
    if existing_movie:
        await message.reply(
            f"ℹ️ Bu xabar allaqachon saqlangan: <b>#{existing_movie.code}</b>"
        )
        return

    result = await _save_movie_from_message(
        session, caption, channel_message_id, photo_file_id
    )
    if result:
        code, created = result
        action = get_text("movie-added", lang) if created else get_text("movie-updated", lang)
        await message.reply(f"🎬 <b>{code}</b> — {action}")
    else:
        await message.reply(
            "⚠️ Kino saqlanmadi: yetarli ma'lumot yo'q (kamida nom+yil yoki nom+janr bo'lishi kerak)"
        )

from aiogram import Router, F
from aiogram.types import Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import settings
from bot.database.crud.movie import upsert_movie
from bot.database.models import User
from bot.services.caption_parser import parse_caption
from bot.services.i18n import get_text

router = Router(name="channel_post")


async def _save_movie_from_message(
    session: AsyncSession,
    caption: str,
    channel_message_id: int,
    photo_file_id: str | None,
) -> tuple[str, bool] | None:
    """Caption'dan kino parse qilib DB'ga saqlaydi. (code, created) yoki None qaytaradi."""
    parsed = parse_caption(caption, channel_message_id)
    if not parsed:
        return None

    _, created = await upsert_movie(
        session=session,
        code=parsed.code,
        channel_message_id=channel_message_id,
        title_uz=parsed.title_uz,
        title_ru=parsed.title_ru,
        title_en=parsed.title_en,
        description_uz=parsed.description_uz,
        description_ru=parsed.description_ru,
        description_en=parsed.description_en,
        year=parsed.year,
        duration=parsed.duration,
        country=parsed.country,
        director=parsed.director,
        cast=parsed.cast,
        imdb_rating=parsed.imdb_rating,
        kinopoisk_rating=parsed.kinopoisk_rating,
        age_rating=parsed.age_rating,
        poster_file_id=photo_file_id,
    )
    return parsed.code, created


# ── Kanalga yangi post tushganda avtomatik saqlash ────────────────────────────

@router.channel_post(F.chat.id == settings.movie_channel_id)
async def handle_new_channel_post(message: Message, session: AsyncSession) -> None:
    """Kino kanaliga yangi xabar kelganda avtomatik DB'ga yozish."""
    caption = message.caption or message.text
    if not caption:
        return

    photo_file_id = message.photo[-1].file_id if message.photo else None

    result = await _save_movie_from_message(session, caption, message.message_id, photo_file_id)
    if result:
        code, created = result
        action = "qo'shildi" if created else "yangilandi"
        logger.info(f"Kanal post: #{code} {action} (msg_id={message.message_id})")
    else:
        logger.debug(f"Kanal post {message.message_id}: kod topilmadi, o'tkazildi")


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
    from bot.handlers.admin.panel import is_admin

    if not is_admin(message.from_user.id, db_user):
        return

    channel_message_id = message.forward_origin.message_id
    caption = message.caption or message.text

    if not caption:
        await message.reply(get_text("forward-no-caption", lang))
        return

    photo_file_id = message.photo[-1].file_id if message.photo else None

    result = await _save_movie_from_message(session, caption, channel_message_id, photo_file_id)
    if result:
        code, created = result
        action = get_text("movie-added", lang) if created else get_text("movie-updated", lang)
        await message.reply(f"🎬 <b>{code}</b> — {action}")
    else:
        await message.reply(get_text("forward-no-code", lang))

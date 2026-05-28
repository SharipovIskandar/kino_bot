from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional, List

from sqlalchemy import (
    BigInteger, Boolean, DateTime, Enum, Float, ForeignKey,
    Integer, String, Text, UniqueConstraint, func, ARRAY,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.database.connection import Base


# ══════════════════════════════════════════════════════════════════════════════
#  ENUMS
# ══════════════════════════════════════════════════════════════════════════════

class Language(str, enum.Enum):
    UZ = "uz"
    RU = "ru"
    EN = "en"


class AdminRole(str, enum.Enum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    MODERATOR = "moderator"


class BroadcastTarget(str, enum.Enum):
    ALL = "all"
    ACTIVE_7D = "active_7d"
    ACTIVE_30D = "active_30d"
    LANG_UZ = "lang_uz"
    LANG_RU = "lang_ru"
    LANG_EN = "lang_en"


class BroadcastStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MediaType(str, enum.Enum):
    TEXT = "text"
    PHOTO = "photo"
    VIDEO = "video"
    DOCUMENT = "document"
    ANIMATION = "animation"


class MovieLanguageType(str, enum.Enum):
    ORIGINAL = "original"
    DUBBED_UZ = "dubbed_uz"
    DUBBED_RU = "dubbed_ru"
    SUBTITLED_UZ = "subtitled_uz"
    SUBTITLED_RU = "subtitled_ru"
    SUBTITLED_EN = "subtitled_en"


class SyncStatus(str, enum.Enum):
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


# ══════════════════════════════════════════════════════════════════════════════
#  USER
# ══════════════════════════════════════════════════════════════════════════════

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    full_name: Mapped[str] = mapped_column(String(256), nullable=False)
    language: Mapped[Language] = mapped_column(
        Enum(Language, values_callable=lambda x: [e.value for e in x]),
        default=Language.UZ, nullable=False
    )

    # Moderatsiya
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False)
    ban_reason: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    banned_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    banned_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)  # admin telegram_id

    # Faollik
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_active_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relations
    movie_views: Mapped[List["MovieView"]] = relationship(
        back_populates="user", lazy="selectin"
    )
    admin_profile: Mapped[Optional["Admin"]] = relationship(
        back_populates="user", uselist=False, lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<User id={self.telegram_id} name={self.full_name!r}>"


# ══════════════════════════════════════════════════════════════════════════════
#  GENRE
# ══════════════════════════════════════════════════════════════════════════════

class Genre(Base):
    __tablename__ = "genres"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)

    movies: Mapped[List["Movie"]] = relationship(
        secondary="movie_genres", back_populates="genres"
    )

    def get_name(self, lang: str = "uz") -> str:
        return self.name


# ══════════════════════════════════════════════════════════════════════════════
#  MOVIE
# ══════════════════════════════════════════════════════════════════════════════

class Movie(Base):
    __tablename__ = "movies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Identifikatsiya
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    channel_message_id: Mapped[int] = mapped_column(BigInteger, nullable=False, unique=True, index=True)

    # Nom va tavsif (faqat o'zbek)
    title: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Metadata
    year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    duration: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # daqiqalarda
    country: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    language_type: Mapped[Optional[MovieLanguageType]] = mapped_column(
        Enum(MovieLanguageType, values_callable=lambda x: [e.value for e in x]), nullable=True
    )
    director: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    cast: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # vergul bilan

    # Reytinglar
    imdb_rating: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    kinopoisk_rating: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    age_rating: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)  # "12+", "18+" etc

    # Telegram
    poster_file_id: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    # Statistika
    view_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Vaqt
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relations
    genres: Mapped[List["Genre"]] = relationship(
        secondary="movie_genres", back_populates="movies"
    )
    views: Mapped[List["MovieView"]] = relationship(back_populates="movie")

    def get_title(self, lang: str = "uz") -> str:
        return self.title or self.code

    def get_description(self, lang: str = "uz") -> str:
        return self.description or ""

    def __repr__(self) -> str:
        return f"<Movie code={self.code!r} title={self.title!r}>"


class MovieGenre(Base):
    """Movie ↔ Genre ko'p-ko'pga aloqa jadvali"""
    __tablename__ = "movie_genres"

    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True)
    genre_id: Mapped[int] = mapped_column(ForeignKey("genres.id", ondelete="CASCADE"), primary_key=True)


# ══════════════════════════════════════════════════════════════════════════════
#  MOVIE VIEW (Analitika)
# ══════════════════════════════════════════════════════════════════════════════

class MovieView(Base):
    __tablename__ = "movie_views"
    __table_args__ = (
        UniqueConstraint("user_id", "movie_id", name="uq_movie_views_user_movie"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id", ondelete="CASCADE"), nullable=False, index=True)
    viewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    user: Mapped["User"] = relationship(back_populates="movie_views")
    movie: Mapped["Movie"] = relationship(back_populates="views")


# ══════════════════════════════════════════════════════════════════════════════
#  MANDATORY CHANNEL
# ══════════════════════════════════════════════════════════════════════════════

class MandatoryChannel(Base):
    __tablename__ = "mandatory_channels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    channel_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    channel_username: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    channel_title: Mapped[str] = mapped_column(String(256), nullable=False)
    invite_link: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    order: Mapped[int] = mapped_column(Integer, default=0)  # ko'rsatish tartibi

    added_by: Mapped[int] = mapped_column(BigInteger, nullable=False)  # admin telegram_id
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:
        return f"<MandatoryChannel id={self.channel_id} title={self.channel_title!r}>"


# ══════════════════════════════════════════════════════════════════════════════
#  ADMIN
# ══════════════════════════════════════════════════════════════════════════════

class Admin(Base):
    __tablename__ = "admins"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    role: Mapped[AdminRole] = mapped_column(
        Enum(AdminRole, values_callable=lambda x: [e.value for e in x]),
        default=AdminRole.ADMIN, nullable=False
    )

    added_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)  # super_admin telegram_id
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="admin_profile")


# ══════════════════════════════════════════════════════════════════════════════
#  BROADCAST
# ══════════════════════════════════════════════════════════════════════════════

class BroadcastMessage(Base):
    __tablename__ = "broadcast_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    media_file_id: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    media_type: Mapped[Optional[MediaType]] = mapped_column(
        Enum(MediaType, values_callable=lambda x: [e.value for e in x]), nullable=True
    )

    target: Mapped[BroadcastTarget] = mapped_column(
        Enum(BroadcastTarget, values_callable=lambda x: [e.value for e in x]),
        default=BroadcastTarget.ALL
    )
    status: Mapped[BroadcastStatus] = mapped_column(
        Enum(BroadcastStatus, values_callable=lambda x: [e.value for e in x]),
        default=BroadcastStatus.PENDING
    )

    total_users: Mapped[int] = mapped_column(Integer, default=0)
    total_sent: Mapped[int] = mapped_column(Integer, default=0)
    total_failed: Mapped[int] = mapped_column(Integer, default=0)

    created_by: Mapped[int] = mapped_column(BigInteger, nullable=False)  # admin telegram_id
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


# ══════════════════════════════════════════════════════════════════════════════
#  SYNC LOG
# ══════════════════════════════════════════════════════════════════════════════

class SyncLog(Base):
    __tablename__ = "sync_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    status: Mapped[SyncStatus] = mapped_column(
        Enum(SyncStatus, values_callable=lambda x: [e.value for e in x]),
        default=SyncStatus.RUNNING
    )

    movies_added: Mapped[int] = mapped_column(Integer, default=0)
    movies_updated: Mapped[int] = mapped_column(Integer, default=0)
    movies_skipped: Mapped[int] = mapped_column(Integer, default=0)

    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    triggered_by: Mapped[int] = mapped_column(BigInteger, nullable=False)  # admin telegram_id
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


# ══════════════════════════════════════════════════════════════════════════════
#  ADMIN ACTION LOG (Audit)
# ══════════════════════════════════════════════════════════════════════════════

class AdminAction(Base):
    __tablename__ = "admin_actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    admin_telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    action_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    details: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

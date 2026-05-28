"""single_language_refactor: title_uz->title, description_uz->description, channel_message_id unique, genre.name

Revision ID: 003_single_language_refactor
Revises: 002_movie_views_unique
Create Date: 2026-05-28

O'zgartirishlar:
- movies.title_uz RENAME -> title
- movies.title_ru, movies.title_en DROP
- movies.description_uz RENAME -> description
- movies.description_ru, movies.description_en DROP
- movies.channel_message_id unique index qo'shish
- genres.name_uz RENAME -> name
- genres.name_ru, genres.name_en DROP
"""
from alembic import op
import sqlalchemy as sa

revision = "003_single_language_refactor"
down_revision = "002_movie_views_unique"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── movies jadvalida nom/tavsif ustunlarini o'zgartirish ──────────────────

    # title_uz -> title
    op.alter_column("movies", "title_uz", new_column_name="title")

    # title_ru va title_en o'chirish (mavjud bo'lsa)
    try:
        op.drop_column("movies", "title_ru")
    except Exception:
        pass
    try:
        op.drop_column("movies", "title_en")
    except Exception:
        pass

    # description_uz -> description
    op.alter_column("movies", "description_uz", new_column_name="description")

    # description_ru va description_en o'chirish (mavjud bo'lsa)
    try:
        op.drop_column("movies", "description_ru")
    except Exception:
        pass
    try:
        op.drop_column("movies", "description_en")
    except Exception:
        pass

    # ── channel_message_id bo'yicha unique index ──────────────────────────────
    # Avval dublikat yozuvlarni tozalash (eski data bo'lsa)
    op.execute("""
        DELETE FROM movies
        WHERE id NOT IN (
            SELECT MIN(id)
            FROM movies
            GROUP BY channel_message_id
        )
        AND channel_message_id IS NOT NULL
    """)

    op.create_index(
        "ix_movies_channel_message_id",
        "movies",
        ["channel_message_id"],
        unique=True,
    )

    # ── genres jadvalida ustunlarni o'zgartirish ──────────────────────────────

    # name_uz -> name
    try:
        op.alter_column("genres", "name_uz", new_column_name="name")
    except Exception:
        # Agar allaqachon 'name' bo'lsa yoki 'name_uz' yo'q bo'lsa
        pass

    # name_ru va name_en o'chirish (mavjud bo'lsa)
    try:
        op.drop_column("genres", "name_ru")
    except Exception:
        pass
    try:
        op.drop_column("genres", "name_en")
    except Exception:
        pass


def downgrade() -> None:
    # ── genres jadvalini qaytarish ────────────────────────────────────────────
    try:
        op.alter_column("genres", "name", new_column_name="name_uz")
    except Exception:
        pass
    try:
        op.add_column("genres", sa.Column("name_ru", sa.String(64), nullable=True))
        op.add_column("genres", sa.Column("name_en", sa.String(64), nullable=True))
    except Exception:
        pass

    # ── movies jadvalini qaytarish ────────────────────────────────────────────
    try:
        op.drop_index("ix_movies_channel_message_id", table_name="movies")
    except Exception:
        pass

    try:
        op.add_column("movies", sa.Column("description_ru", sa.Text(), nullable=True))
        op.add_column("movies", sa.Column("description_en", sa.Text(), nullable=True))
        op.alter_column("movies", "description", new_column_name="description_uz")
    except Exception:
        pass

    try:
        op.add_column("movies", sa.Column("title_ru", sa.String(512), nullable=True))
        op.add_column("movies", sa.Column("title_en", sa.String(512), nullable=True))
        op.alter_column("movies", "title", new_column_name="title_uz")
    except Exception:
        pass

"""initial_schema

Revision ID: 001_initial
Revises:
Create Date: 2026-04-19

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── users ──────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(64), nullable=True),
        sa.Column("full_name", sa.String(256), nullable=False),
        sa.Column(
            "language",
            sa.Enum("uz", "ru", "en", name="language"),
            nullable=False,
            server_default="uz",
        ),
        sa.Column("is_banned", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("ban_reason", sa.String(512), nullable=True),
        sa.Column("banned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("banned_by", sa.BigInteger(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "registered_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "last_active_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_telegram_id", "users", ["telegram_id"], unique=True)

    # ── genres ─────────────────────────────────────────────────────────────────
    op.create_table(
        "genres",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name_uz", sa.String(64), nullable=False),
        sa.Column("name_ru", sa.String(64), nullable=False),
        sa.Column("name_en", sa.String(64), nullable=False),
        sa.Column("slug", sa.String(64), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_genres_slug", "genres", ["slug"], unique=True)

    # ── movies ─────────────────────────────────────────────────────────────────
    op.create_table(
        "movies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(32), nullable=False),
        sa.Column("channel_message_id", sa.BigInteger(), nullable=False),
        sa.Column("title_uz", sa.String(512), nullable=True),
        sa.Column("title_ru", sa.String(512), nullable=True),
        sa.Column("title_en", sa.String(512), nullable=True),
        sa.Column("description_uz", sa.Text(), nullable=True),
        sa.Column("description_ru", sa.Text(), nullable=True),
        sa.Column("description_en", sa.Text(), nullable=True),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("duration", sa.Integer(), nullable=True),
        sa.Column("country", sa.String(128), nullable=True),
        sa.Column(
            "language_type",
            sa.Enum(
                "original", "dubbed_uz", "dubbed_ru",
                "subtitled_uz", "subtitled_ru", "subtitled_en",
                name="movielanguagetype",
            ),
            nullable=True,
        ),
        sa.Column("director", sa.String(256), nullable=True),
        sa.Column("cast", sa.Text(), nullable=True),
        sa.Column("imdb_rating", sa.Float(), nullable=True),
        sa.Column("kinopoisk_rating", sa.Float(), nullable=True),
        sa.Column("age_rating", sa.String(8), nullable=True),
        sa.Column("poster_file_id", sa.String(512), nullable=True),
        sa.Column("view_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.func.now(), nullable=False,
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True),
            server_default=sa.func.now(), nullable=False,
        ),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_movies_code", "movies", ["code"], unique=True)

    # ── movie_genres ───────────────────────────────────────────────────────────
    op.create_table(
        "movie_genres",
        sa.Column("movie_id", sa.Integer(), sa.ForeignKey("movies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("genre_id", sa.Integer(), sa.ForeignKey("genres.id", ondelete="CASCADE"), nullable=False),
        sa.PrimaryKeyConstraint("movie_id", "genre_id"),
    )

    # ── movie_views ────────────────────────────────────────────────────────────
    op.create_table(
        "movie_views",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("movie_id", sa.Integer(), sa.ForeignKey("movies.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "viewed_at", sa.DateTime(timezone=True),
            server_default=sa.func.now(), nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_movie_views_user_id", "movie_views", ["user_id"])
    op.create_index("ix_movie_views_movie_id", "movie_views", ["movie_id"])
    op.create_index("ix_movie_views_viewed_at", "movie_views", ["viewed_at"])

    # ── mandatory_channels ─────────────────────────────────────────────────────
    op.create_table(
        "mandatory_channels",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("channel_id", sa.BigInteger(), nullable=False),
        sa.Column("channel_username", sa.String(128), nullable=True),
        sa.Column("channel_title", sa.String(256), nullable=False),
        sa.Column("invite_link", sa.String(512), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("added_by", sa.BigInteger(), nullable=False),
        sa.Column(
            "added_at", sa.DateTime(timezone=True),
            server_default=sa.func.now(), nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("channel_id"),
    )

    # ── admins ─────────────────────────────────────────────────────────────────
    op.create_table(
        "admins",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "role",
            sa.Enum("super_admin", "admin", "moderator", name="adminrole"),
            nullable=False,
            server_default="admin",
        ),
        sa.Column("added_by", sa.BigInteger(), nullable=True),
        sa.Column(
            "added_at", sa.DateTime(timezone=True),
            server_default=sa.func.now(), nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )

    # ── broadcast_messages ─────────────────────────────────────────────────────
    op.create_table(
        "broadcast_messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=True),
        sa.Column("media_file_id", sa.String(512), nullable=True),
        sa.Column(
            "media_type",
            sa.Enum("text", "photo", "video", "document", "animation", name="mediatype"),
            nullable=True,
        ),
        sa.Column(
            "target",
            sa.Enum(
                "all", "active_7d", "active_30d",
                "lang_uz", "lang_ru", "lang_en",
                name="broadcasttarget",
            ),
            nullable=False,
            server_default="all",
        ),
        sa.Column(
            "status",
            sa.Enum("pending", "running", "done", "failed", "cancelled", name="broadcaststatus"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("total_users", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_sent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_by", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.func.now(), nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── sync_logs ──────────────────────────────────────────────────────────────
    op.create_table(
        "sync_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("running", "done", "failed", name="syncstatus"),
            nullable=False,
            server_default="running",
        ),
        sa.Column("movies_added", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("movies_updated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("movies_skipped", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("triggered_by", sa.BigInteger(), nullable=False),
        sa.Column(
            "started_at", sa.DateTime(timezone=True),
            server_default=sa.func.now(), nullable=False,
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── admin_actions ──────────────────────────────────────────────────────────
    op.create_table(
        "admin_actions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("admin_telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("action_type", sa.String(64), nullable=False),
        sa.Column("target_id", sa.String(128), nullable=True),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.func.now(), nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_admin_actions_admin_telegram_id", "admin_actions", ["admin_telegram_id"])
    op.create_index("ix_admin_actions_created_at", "admin_actions", ["created_at"])


def downgrade() -> None:
    op.drop_table("admin_actions")
    op.drop_table("sync_logs")
    op.drop_table("broadcast_messages")
    op.drop_table("admins")
    op.drop_table("mandatory_channels")
    op.drop_table("movie_views")
    op.drop_table("movie_genres")
    op.drop_table("movies")
    op.drop_table("genres")
    op.drop_table("users")

    # Enum larni o'chirish
    for enum_name in [
        "language", "movielanguagetype", "adminrole",
        "mediatype", "broadcasttarget", "broadcaststatus", "syncstatus",
    ]:
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")

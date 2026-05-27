"""movie_views unique constraint (user_id, movie_id)

Revision ID: 002_movie_views_unique
Revises: 001_initial
Create Date: 2026-05-27

"""
from alembic import op

revision = "002_movie_views_unique"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Takroriy yozuvlarni o'chirish (eski data bo'lsa)
    op.execute("""
        DELETE FROM movie_views
        WHERE id NOT IN (
            SELECT MIN(id)
            FROM movie_views
            GROUP BY user_id, movie_id
        )
    """)
    op.create_unique_constraint(
        "uq_movie_views_user_movie",
        "movie_views",
        ["user_id", "movie_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_movie_views_user_movie", "movie_views", type_="unique")

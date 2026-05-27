import os
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool

from alembic import context

# Loyiha root'ini path'ga qo'shamiz
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bot.database.models import Base  # noqa: E402  — barcha modellar import
from bot.config import settings       # noqa: E402

# Alembic Config object
config = context.config

# Logging setup
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Models metadata — autogenerate uchun
target_metadata = Base.metadata

# DB URL'ni .env dan olamiz (alembic.ini'dagi url'ni override qilamiz)
config.set_main_option("sqlalchemy.url", settings.database_url_sync)


def run_migrations_offline() -> None:
    """Offline rejimda migration — DB'ga ulanmasdan SQL fayllar generatsiya qiladi"""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Online rejimda migration — to'g'ridan-to'g'ri DB'ga qo'llaniladi"""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

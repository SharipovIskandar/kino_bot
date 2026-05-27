from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import computed_field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Bot ──────────────────────────────────────────────────────────────
    bot_token: str
    bot_mode: str = "polling"

    # Super adminlar (vergul bilan ajratilgan ID lar)
    super_admin_ids: str = ""

    @computed_field
    @property
    def super_admin_list(self) -> List[int]:
        if not self.super_admin_ids:
            return []
        return [int(x.strip()) for x in self.super_admin_ids.split(",") if x.strip()]

    # ── Kino kanali ──────────────────────────────────────────────────────
    movie_channel_id: int

    # ── Database ─────────────────────────────────────────────────────────
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "kinobot"
    db_user: str = "kinobot_user"
    db_pass: str = ""

    @computed_field
    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.db_user}:{self.db_pass}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @computed_field
    @property
    def database_url_sync(self) -> str:
        """Alembic uchun sync URL"""
        return (
            f"postgresql+psycopg2://{self.db_user}:{self.db_pass}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    # ── Redis ─────────────────────────────────────────────────────────────
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0

    @computed_field
    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    # ── Bot sozlamalari ───────────────────────────────────────────────────
    default_language: str = "uz"
    throttle_rate: int = 10  # 1 daqiqada maksimal so'rovlar

    # Webhook (faqat bot_mode=webhook bo'lsa)
    webhook_host: str = ""
    webhook_path: str = "/webhook"
    webhook_port: int = 8080

    @computed_field
    @property
    def webhook_url(self) -> str:
        return f"{self.webhook_host}{self.webhook_path}"


# Global settings instance
settings = Settings()

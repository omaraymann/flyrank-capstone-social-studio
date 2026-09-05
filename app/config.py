from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./social_studio.db"
    jwt_secret: str = "development-only-change-me"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 60
    url_fetch_timeout_seconds: float = 10
    url_fetch_max_bytes: int = 2_000_000
    discord_webhook_url: str | None = None
    worker_poll_seconds: float = 2
    worker_lease_seconds: int = 30
    max_publish_attempts: int = 3
    retry_base_seconds: int = 5

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings():
    return Settings()


settings = get_settings()

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "IT Cube Inventory"
    database_url: str = "sqlite:///./inventory.db"
    admin_password: str = "change_me"
    api_key_secret: str = "change_api_secret"
    jwt_secret: str = "change_jwt_secret"

    api_key_period_seconds: int = 60
    api_key_grace_periods: int = 1
    access_token_expire_minutes: int = 24 * 60

    cors_origins: list[str] = Field(default_factory=lambda: ["*"])

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()

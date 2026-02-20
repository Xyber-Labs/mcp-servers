from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

_project_root = Path(__file__).resolve().parents[2]
_env_file = _project_root / ".env"


class ApifySettings(BaseSettings):
    """Apify API configuration."""

    # Read from APIFY_TOKEN (no prefix duplication)
    apify_token: str
    actor_name: str = "apidojo/twitter-scraper-lite"

    model_config = SettingsConfigDict(
        env_file=_env_file,
        env_file_encoding="utf-8",
        extra="ignore",
    )


class DatabaseSettings(BaseSettings):
    """Database configuration for Postgres cache."""

    db_user: str | None = None
    db_password: str | None = None
    db_host: str | None = None
    db_name: str = "mcp_twitter_apify"
    db_port: str = "5432"

    # Cache TTL defaults (in seconds)
    cache_ttl_topic_latest: int = 900  # 15 min
    cache_ttl_topic_top: int = 86400  # 24 hours
    cache_ttl_profile: int = 1800  # 30 min
    cache_ttl_replies: int = 3600  # 1 hour

    model_config = SettingsConfigDict(
        env_file=_env_file,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("db_port", mode="before")
    @classmethod
    def strip_port_prefix(cls, v: str) -> str:
        """Handle port values like 'tcp://host:5432' by extracting just the port."""
        if isinstance(v, str) and ":" in v:
            return v.split(":")[-1]
        return v

    @computed_field
    @property
    def is_configured(self) -> bool:
        """Database is configured if all required fields are set."""
        return all([self.db_user, self.db_password, self.db_host])

    @computed_field
    @property
    def database_url(self) -> str | None:
        """Build DATABASE_URL only if all required fields are configured."""
        if not self.is_configured:
            return None
        return f"postgresql+psycopg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"


class AppSettings(BaseSettings):
    """Application settings for the MCP Twitter scraper CLI."""

    host: str = "0.0.0.0"
    port: int = 8002
    logging_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    hot_reload: bool = False

    model_config = SettingsConfigDict(
        env_file=_env_file,
        env_file_encoding="utf-8",
        env_prefix="MCP_TWITTER_",
        extra="ignore",
    )

    @computed_field
    @property
    def apify(self) -> ApifySettings:
        return ApifySettings()

    @computed_field
    @property
    def database(self) -> DatabaseSettings:
        return DatabaseSettings()


@lru_cache(maxsize=1)
def get_app_settings() -> AppSettings:
    return AppSettings()

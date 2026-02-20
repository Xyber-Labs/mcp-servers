"""
This module defines configuration for the MCP YouTube server.

Main responsibility: Define and load application configuration, exposing cached helpers to access these settings.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class AppSettings(BaseSettings):
    """
    Application settings for the MCP YouTube Server.

    Configuration can be provided via environment variables:

    # Server settings:
    MCP_YOUTUBE_HOST=0.0.0.0
    MCP_YOUTUBE_PORT=8002
    MCP_YOUTUBE_LOGGING_LEVEL=INFO

    # Apify token (required for YouTube search):
    MCP_YOUTUBE_APIFY_TOKEN=your_token_here
    # Or use flat name: APIFY_TOKEN=your_token_here

    # Database settings (optional - for caching):
    MCP_YOUTUBE_DB_NAME=mcp_youtube
    MCP_YOUTUBE_DB_USER=postgres
    MCP_YOUTUBE_DB_PASSWORD=your_password
    MCP_YOUTUBE_DB_HOST=localhost
    MCP_YOUTUBE_DB_PORT=5432
    # Or use flat names: DB_NAME, DB_USER, etc.

    Note: Database is optional. If not configured, service runs without caching.
    """

    # --- Server Settings ---
    host: str = "0.0.0.0"
    port: int = 8002
    logging_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    hot_reload: bool = False

    # --- Apify Configuration ---    
    apify_token: str | None = Field(
        default=None,
        validation_alias=AliasChoices("MCP_YOUTUBE_APIFY_TOKEN", "APIFY_TOKEN"),
    )

    # --- YouTube Service Configuration ---
    delay_between_requests: float = 1.0
    max_results: int = 10
    num_videos: int = 5
    query: str = "quantum computing basics"

    # --- Logging Configuration ---
    log_level: str = "INFO"
    log_format: str = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    log_file: str = "logs/mcp_youtube.log"

    # --- Database Configuration (Optional) ---
    db_name: str | None = None
    db_user: str | None = None
    db_password: str | None = None
    db_host: str | None = None
    db_port: int | None = None

    @computed_field
    @property
    def database_url(self) -> str | None:
        """
        Compute DATABASE_URL using psycopg3 driver.

        Returns None if any required field is missing, allowing the service
        to run without database caching.
        """
        if not all([self.db_name, self.db_user, self.db_password, self.db_host, self.db_port]):
            return None

        url = f"postgresql+psycopg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
        # Avoid leaking credentials in logs
        logger.info(
            "Database configured: postgresql+psycopg://%s:***@%s:%s/%s",
            self.db_user,
            self.db_host,
            self.db_port,
            self.db_name,
        )
        return url

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="MCP_YOUTUBE_",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_app_settings() -> AppSettings:
    """Get cached application settings."""
    return AppSettings()

"""
This module defines configuration for the MCP Wikipedia server.

Main responsibility: Define and load application configuration, exposing cached helpers to access these settings.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class AppSettings(BaseSettings):
    """
    Application settings for the MCP Wikipedia Server.

    Configuration can be provided via environment variables:

    # Server settings:
    MCP_WIKIPEDIA_HOST=0.0.0.0
    MCP_WIKIPEDIA_PORT=8006
    MCP_WIKIPEDIA_LOGGING_LEVEL=INFO
    """

    host: str = "0.0.0.0"
    port: int = 8006
    logging_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    hot_reload: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="MCP_WIKIPEDIA_",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_app_settings() -> AppSettings:
    """Get cached application settings."""
    return AppSettings()

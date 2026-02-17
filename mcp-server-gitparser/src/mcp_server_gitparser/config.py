"""
This module defines configuration for the MCP Gitparser server.

Main responsibility: Define and load application configuration, exposing cached helpers to access these settings.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class AppSettings(BaseSettings):
    """
    Application settings for the MCP Gitparser Server.

    Configuration can be provided via environment variables:

    # Server settings:
    MCP_GITPARSER_HOST=0.0.0.0
    MCP_GITPARSER_PORT=8000
    MCP_GITPARSER_LOGGING_LEVEL=INFO
    MCP_GITPARSER_DOCS_DIR=docs
    """

    host: str = "0.0.0.0"
    port: int = 8000
    logging_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    hot_reload: bool = False

    docs_dir: str = "docs"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="MCP_GITPARSER_",
        case_sensitive=False,
        extra="ignore",
    )

    @computed_field
    @property
    def project_root(self) -> Path:
        """Get project root directory (2 levels up from this file)."""
        return Path(__file__).resolve().parents[2]

    @computed_field
    @property
    def docs_path(self) -> Path:
        """Get full path to docs directory."""
        return self.project_root / self.docs_dir


@lru_cache(maxsize=1)
def get_app_settings() -> AppSettings:
    """Get cached application settings."""
    return AppSettings()

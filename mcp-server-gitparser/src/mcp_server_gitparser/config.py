"""
Configuration module for the MCP Gitparser server.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

# Load environment variables from the repo-root .env file (if present).
_project_root = Path(__file__).resolve().parents[2]
_env_file = _project_root / ".env"
load_dotenv(dotenv_path=_env_file)


class AppSettings(BaseSettings):
    """Application settings for the MCP Gitparser server."""

    host: str = "0.0.0.0"
    port: int = 8000
    logging_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    hot_reload: bool = False

    docs_dir: str = "docs"

    model_config = SettingsConfigDict(
        env_file=_env_file,
        env_file_encoding="utf-8",
        env_prefix="MCP_GITPARSER_",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",
    )

    @computed_field
    @property
    def project_root(self) -> Path:
        return _project_root

    @computed_field
    @property
    def docs_path(self) -> Path:
        return self.project_root / self.docs_dir


@lru_cache(maxsize=1)
def get_app_settings() -> AppSettings:
    return AppSettings()


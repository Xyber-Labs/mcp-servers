from __future__ import annotations

import logging
from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class AppSettings(BaseSettings):
    """
    Application settings for the Together Image Generation MCP Server.

    Configuration can be provided via environment variables using nested notation:

    # Server settings:
    MCP_TOGETHER_IMGEN_HOST=0.0.0.0
    MCP_TOGETHER_IMGEN_PORT=8000
    """

    # --- Server Settings ---
    host: str = "0.0.0.0"
    port: int = 8000
    logging_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    hot_reload: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="MCP_TOGETHER_IMGEN_",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_app_settings() -> AppSettings:
    return AppSettings()

"""
Application configuration module.

Main responsibility: Define and load application configuration, exposing cached helpers to access these settings.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """
    Application settings for the MCP Quill server.

    Configuration can be provided via environment variables using nested notation:

    # Server settings:
    MCP_QUILL_HOST=0.0.0.0
    MCP_QUILL_PORT=8001

    # Quill API settings:
    MCP_QUILL_QUILL__API_KEY=your_api_key
    MCP_QUILL_QUILL__BASE_URL=https://check-api.quillai.network/api/v1

    # DexScreener API settings:
    MCP_QUILL_DEXSCREENER__BASE_URL=https://api.dexscreener.com/latest/dex/search
    """

    # --- Server Settings ---
    host: str = "0.0.0.0"
    port: int = 8001
    logging_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    hot_reload: bool = False

    # --- Quill API Settings ---
    quill__api_key: str | None = None
    quill__base_url: str = "https://check-api.quillai.network/api/v1"

    # --- DexScreener API Settings ---
    dexscreener__base_url: str = "https://api.dexscreener.com/latest/dex/search"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="MCP_QUILL_",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_app_settings() -> AppSettings:
    return AppSettings()

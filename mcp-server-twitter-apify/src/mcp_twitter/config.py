"""
Configuration module for the MCP Twitter scraper CLI.

Loads `.env` from repo root when running from source checkout.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict
from mcp_twitter.logger import get_logger

logger = get_logger(__name__)


# Load environment variables from the repo-root .env file (if present).
# File location: <repo>/src/mcp_twitter/config.py -> repo root is 2 levels up.
_project_root = Path(__file__).resolve().parents[2]
_env_file = _project_root / ".env"
load_dotenv(dotenv_path=_env_file)


class ApifyConfig(BaseModel):
    """Apify API configuration."""

    # Prefer the common `APIFY_TOKEN`, but allow nested form too.
    apify_token: str | None = os.getenv("APIFY_TOKEN") or os.getenv(
        "MCP_TWITTER__APIFY__APIFY_TOKEN"
    )
    
    # Actor name can be set via APIFY_ACTOR_NAME or MCP_TWITTER__APIFY__ACTOR_NAME
    actor_name: str = os.getenv("APIFY_ACTOR_NAME") or os.getenv(
        "MCP_TWITTER__APIFY__ACTOR_NAME",
        "apidojo/twitter-scraper-lite",  # Default fallback
    )


class DatabaseConfig(BaseModel):
    """Database configuration for Postgres cache."""

    DB_NAME: str = os.getenv("DB_NAME", "mcp_twitter_apify")
    DB_USER: str = os.getenv("DB_USER", "postgres")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "postgres")
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT_RAW: str = os.getenv("DB_PORT", "5432")
    DB_PORT: str = (
        DB_PORT_RAW.split(":")[0] if ":" in DB_PORT_RAW else DB_PORT_RAW
    )
    DATABASE_URL: str = (
        f"postgresql+psycopg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )
    logger.info(f"DEBUG: Connecting to: {DATABASE_URL}")

    # Cache TTL defaults (in seconds)
    cache_ttl_topic_latest: int = int(os.getenv("CACHE_TTL_TOPIC_LATEST", "900"))  # 15 min
    cache_ttl_topic_top: int = int(os.getenv("CACHE_TTL_TOPIC_TOP", "86400"))  # 24 hours
    cache_ttl_profile: int = int(os.getenv("CACHE_TTL_PROFILE", "1800"))  # 30 min
    cache_ttl_replies: int = int(os.getenv("CACHE_TTL_REPLIES", "3600"))  # 1 hour


class AppSettings(BaseSettings):
    """Application settings for the MCP Twitter scraper CLI."""

    host: str = "0.0.0.0"
    port: int = 8002
    logging_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    hot_reload: bool = False

    apify: ApifyConfig = ApifyConfig()
    database: DatabaseConfig = DatabaseConfig()

    model_config = SettingsConfigDict(
        env_file=_env_file,
        env_file_encoding="utf-8",
        env_prefix="MCP_TWITTER_",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",
    )



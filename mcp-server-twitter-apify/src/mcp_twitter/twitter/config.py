"""
This module should be changed to match the exact configuration options and environment variable prefixes for your service.

Main responsibility: Define and load configuration settings for the twitter service using Pydantic settings and a cached accessor.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

# --- Configuration Model --- 


class TwitterConfig(BaseSettings):
    """
    Configuration for the Twitter service.

    Attributes:
        apify_token: Apify API token (optional, can be provided via header instead)
        timeout_seconds: Timeout for API requests in seconds
        enable_caching: Whether to enable caching of twitter responses
        cache_ttl_seconds: Cache time-to-live in seconds
        actor_name: Apify actor name to use for scraping

    """

    # Pydantic Settings configuration
    model_config = SettingsConfigDict(
        env_prefix="TWITTER_",  # Look for env vars like TWITTER_APIFY_TOKEN
        env_file=".env",  # Load from .env file if it exists
        env_file_encoding="utf-8",
        extra="ignore",  # Ignore extra fields from the environment
        case_sensitive=False,  # Environment variables are case-insensitive
    )

    apify_token: str = ""
    timeout_seconds: int = 600
    enable_caching: bool = True
    cache_ttl_seconds: int = 300  # 5 minutes
    actor_name: str = "apidojo/twitter-scraper-lite"


@lru_cache(maxsize=1)
def get_twitter_config() -> TwitterConfig:
    """
    Get a cached instance of TwitterConfig.

    Returns:
        Validated TwitterConfig instance

    Raises:
        ValidationError: If configuration validation fails (from Pydantic)

    """
    config = TwitterConfig()
    return config


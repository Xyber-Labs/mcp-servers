"""
This module should be changed to match the exact configuration options and environment variable prefixes for your service.

Main responsibility: Define and load configuration settings for the weather service using Pydantic settings and a cached accessor.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

# --- Configuration Model --- #


class WeatherConfig(BaseSettings):
    """
    Configuration for the Weather service.

    Attributes:
        timeout_seconds: Timeout for API requests in seconds
        enable_caching: Whether to enable caching of weather responses
        cache_ttl_seconds: Cache time-to-live in seconds

    """

    # Pydantic Settings configuration
    model_config = SettingsConfigDict(
        env_prefix="WEATHER_",  # Look for env vars like WEATHER_API_KEY
        env_file=".env",  # Load from .env file if it exists
        env_file_encoding="utf-8",
        extra="ignore",  # Ignore extra fields from the environment
        case_sensitive=False,  # Environment variables are case-insensitive
    )

    timeout_seconds: int = 10
    enable_caching: bool = True
    cache_ttl_seconds: int = 300  # 5 minutes


@lru_cache(maxsize=1)
def get_weather_config() -> WeatherConfig:
    """
    Get a cached instance of WeatherConfig.

    Returns:
        Validated WeatherConfig instance

    Raises:
        ValidationError: If configuration validation fails (from Pydantic)

    """
    config = WeatherConfig()
    return config

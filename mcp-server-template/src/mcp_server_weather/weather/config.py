"""
This module will mostly stay the same for all MCP servers
This module contains the FastAPI application factory and resource lifecycle management.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

# --- Configuration Model --- #


class WeatherConfig(BaseSettings):
    """
    Configuration for the Weather service.

    Attributes:
        api_key: OpenWeatherMap API key (required)
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

    api_key: str
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

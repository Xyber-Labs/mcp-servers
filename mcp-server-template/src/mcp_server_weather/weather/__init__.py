"""
This module should be changed to fit your domain-specific service layer, using it as a central place to expose clients, configuration, errors, and models.

Main responsibility: Provide a public facade for the weather service by re-exporting the client, configuration helpers, error types, and data models.
"""

from mcp_server_weather.weather.config import (
    WeatherConfig,
    get_weather_config,
)
from mcp_server_weather.weather.errors import (
    WeatherApiError,
    WeatherClientError,
    WeatherConfigError,
)
from mcp_server_weather.weather.models import WeatherData
from mcp_server_weather.weather.module import WeatherClient, get_weather_client

__all__ = [
    "WeatherClient",
    "get_weather_client",
    "WeatherConfig",
    "get_weather_config",
    "WeatherApiError",
    "WeatherClientError",
    "WeatherConfigError",
    "WeatherData",
]

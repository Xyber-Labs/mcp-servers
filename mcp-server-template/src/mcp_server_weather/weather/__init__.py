"""
This file should change to fit your business logic needs
It exposes abstractions that your module serves
In sake of typing and exception handling
it is also likely to expose base error classes and configuration models
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

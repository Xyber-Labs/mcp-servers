"""
This module will mostly stay the same for all MCP servers
This module contains the FastAPI application factory and resource lifecycle management.
"""


class WeatherServiceError(Exception):
    """Base exception for all weather service related errors."""


class WeatherConfigError(WeatherServiceError):
    """Raised for weather configuration errors."""


class WeatherApiError(WeatherServiceError):
    """Raised for OpenWeatherMap API errors."""


class WeatherClientError(WeatherServiceError):
    """Raised for unexpected client-side errors."""

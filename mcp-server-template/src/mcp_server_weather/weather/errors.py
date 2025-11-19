"""
This module should be changed to match the exact error types and handling logic for your service.

Main responsibility: Define a small, typed exception hierarchy for configuration, API, and client errors in the weather service.
"""


class WeatherServiceError(Exception):
    """Base exception for all weather service related errors."""


class WeatherConfigError(WeatherServiceError):
    """Raised for weather configuration errors."""


class WeatherApiError(WeatherServiceError):
    """Raised for OpenWeatherMap API errors."""


class WeatherClientError(WeatherServiceError):
    """Raised for unexpected client-side errors."""

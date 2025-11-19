"""
This module should be changed as you add or modify dependencies for your own business logic, while keeping the pattern of thin wrappers around shared clients.

Main responsibility: Provide FastAPI dependency functions that expose shared service clients to routers and tools.
"""

from fastapi import Request

from mcp_server_weather.weather import WeatherClient
from mcp_server_weather.weather import get_weather_client as _get_weather_client


def get_weather_client(request: Request) -> WeatherClient:
    """
    Dependency to get the WeatherClient instance.

    For this template we use the globally cached WeatherClient provided by the
    weather module so that both REST and MCP calls share the same client.
    """
    return _get_weather_client()

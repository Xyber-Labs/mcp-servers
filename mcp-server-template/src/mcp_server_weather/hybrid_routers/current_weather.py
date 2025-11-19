"""
This module should be changed to match how your application exposes free hybrid (REST + MCP) endpoints for fetching current domain-specific data.

Main responsibility: Implement a free hybrid endpoint that retrieves current weather data for a location, using the shared weather client and FastAPI dependencies.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Header, HTTPException

from mcp_server_weather.dependencies import get_weather_client
from mcp_server_weather.schemas import LocationRequest
from mcp_server_weather.weather import (
    WeatherApiError,
    WeatherClient,
    WeatherClientError,
)

logger = logging.getLogger(__name__)
router = APIRouter()
API_KEY_HEADER = "Weather-Api-Key"


@router.post(
    "/current",
    tags=["Weather"],
    # IMPORTANT: The `operation_id` is crucial. It serves as the stable,
    # machine-readable name for this endpoint and is used for both MCP tool
    # generation and the dynamic pricing system. It must be unique.
    operation_id="get_current_weather",
)
async def get_current_weather(
    location: LocationRequest,
    weather_api_key: str | None = Header(
        default=None,
        alias=API_KEY_HEADER,
        description=(
            "OpenWeatherMap API key used to authorize this weather request. "
            "This header is required for all calls that fetch live weather data."
        ),
    ),
    weather_client: WeatherClient = Depends(get_weather_client),
) -> dict[str, str]:
    """
    Retrieves current weather data for a specified location.

    This endpoint is available to both REST API consumers and AI agents via MCP.

    Authentication / API key usage:
    - Clients MUST provide a valid OpenWeatherMap API key via the
      `Weather-Api-Key` HTTP header.
    - If the header is missing or empty, the server responds with HTTP 400 and
      the message "Weather-Api-Key header is required".
    - If the upstream provider rejects the key (e.g. 401), the error is
      translated into a 503 Service Unavailable response with a message like
      "OpenWeatherMap API HTTP error: 401".
    """
    api_key = weather_api_key
    if not api_key:
        raise HTTPException(
            status_code=400,
            detail=f"{API_KEY_HEADER} header is required.",
        )

    try:
        weather_data = await weather_client.get_weather(
            latitude=location.latitude,
            longitude=location.longitude,
            units=location.units,
            api_key=api_key,
        )
        result = {
            "state": weather_data.state,
            "temperature": str(weather_data.temperature),
            "humidity": str(weather_data.humidity),
        }
        logger.info(f"Successfully retrieved weather data: {result}")
        return result
    except (WeatherApiError, WeatherClientError) as e:
        logger.error(f"Weather service error: {e}")
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in get_current_weather: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")

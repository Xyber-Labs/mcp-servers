# ==============================================================================
# Hybrid Router Example (Free)
# ------------------------------------------------------------------------------
# This file is a self-contained example of a Hybrid (REST + MCP) endpoint.
# - You can use this file as a template for your own Hybrid endpoints.
# - This endpoint is free and not protected by x402 middleware.
# ==============================================================================

import logging

from fastapi import APIRouter, Depends, HTTPException

from mcp_server_weather.dependencies import get_weather_client
from mcp_server_weather.schemas import LocationRequest
from mcp_server_weather.weather import (
    WeatherApiError,
    WeatherClient,
    WeatherClientError,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/current",
    tags=["Weather"],
    # IMPORTANT: The `operation_id` is crucial. It serves as the stable,
    # machine-readable name for this endpoint and is used for both MCP tool
    # generation and the dynamic pricing system. It must be unique.
    operation_id="get_current_weather",
)
async def get_current_weather(
    request: LocationRequest,
    weather_client: WeatherClient = Depends(get_weather_client),
) -> dict[str, str]:
    """
    Retrieves current weather data for a specified location.

    This endpoint is available to both REST API consumers and AI agents via
    MCP. It demonstrates how to create a hybrid endpoint that serves both
    audiences without duplication.
    """
    try:
        weather_data = await weather_client.get_weather(
            latitude=request.latitude,
            longitude=request.longitude,
            units=request.units,
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

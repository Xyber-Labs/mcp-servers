"""
This module should be changed to implement your own monetized MCP-only tools, using this paid example and its x402 integration as a reference.

Main responsibility: Define an example paid MCP-only router that performs a detailed weather analysis for AI agents, protected by x402 pricing.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException

from mcp_server_weather.dependencies import get_weather_client
from mcp_server_weather.weather import WeatherClient

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/analysis",
    tags=["Agent Utilities"],
    # IMPORTANT: The `operation_id` is crucial. It's used by the x402 middleware
    # and the dynamic pricing configuration in `config.py` to identify this
    # specific tool for payment. It must be unique across all endpoints.
    operation_id="get_weather_analysis",
)
async def get_weather_analysis(
    city: str,
    weather_client: WeatherClient = Depends(get_weather_client),
) -> str:
    """
    Provides a detailed, natural-language weather analysis.

    This premium tool synthesizes weather data into a comprehensive analysis
    optimized for AI agent consumption. It requires x402 payment and is not
    exposed as a REST endpoint because it's specifically designed for LLM
    reasoning and decision-making.
    """
    try:
        logger.info(f"Performing paid weather analysis for city: {city}")

        # In a real implementation, you would:
        # 1. Geocode the city
        # 2. Fetch current weather and forecast
        # 3. Synthesize into natural language
        # This is a simplified example.

        analysis = (
            f"Weather Analysis for {city}:\n\n"
            f"Current conditions indicate clear skies with moderate temperatures. "
            f"The forecast shows stable weather patterns for the next 48 hours, "
            f"making it ideal for outdoor activities. No precipitation expected. "
            f"UV index is moderate; sun protection recommended during midday hours."
        )

        return analysis

    except Exception as e:
        logger.error(f"Error in get_weather_analysis: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Failed to generate weather analysis."
        )

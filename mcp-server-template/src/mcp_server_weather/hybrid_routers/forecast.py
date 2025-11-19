"""
This module should be changed to reflect your own paid hybrid (REST + MCP) endpoints, using this forecast example and its x402 integration as a template.

Main responsibility: Implement a paid hybrid endpoint that returns a multi-day weather forecast, demonstrating monetization across REST and MCP interfaces.
"""

# ==============================================================================
# Hybrid Router Example (Paid)
# ------------------------------------------------------------------------------
# This file is a self-contained example of a paid Hybrid (REST + MCP) endpoint.
# - You can use this file as a template for your own monetized Hybrid endpoints.
# - The price is configured dynamically in `config.py` and `.env`.
# ==============================================================================

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from mcp_server_weather.dependencies import get_weather_client
from mcp_server_weather.weather import WeatherClient

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/forecast",
    tags=["Weather"],
    # IMPORTANT: The `operation_id` is crucial. It's used by the x402 middleware
    # and the dynamic pricing configuration in `config.py` to identify this
    # specific endpoint for payment. It must be unique across all endpoints.
    operation_id="get_weather_forecast",
)
async def get_weather_forecast(
    days: Annotated[int, Query(ge=1, le=14)] = 7,
    weather_client: WeatherClient = Depends(get_weather_client),
) -> dict:
    """
    Retrieves a multi-day weather forecast.

    This is a premium endpoint that requires x402 payment. It is available to
    both REST API consumers and AI agents, demonstrating how to monetize
    hybrid endpoints across both interfaces.
    """
    logger.info(f"Paid forecast endpoint called for {days} days.")
    # In a real implementation, you would use the weather_client to fetch
    # forecast data. This is a simplified example.
    return {
        "location": "Sample City",
        "days": days,
        "forecast": [
            {"day": i + 1, "condition": "Sunny", "high": 75, "low": 60}
            for i in range(days)
        ],
    }

"""
MCP-Only Router Example (Free)
------------------------------------------------------------------------------
This file is a self-contained example of an MCP-Only endpoint.
- You can use this file as a template for your own agent-specific tools.
- This endpoint is free and not protected by x402 middleware.
"""

import logging

from fastapi import APIRouter

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/geolocate",
    tags=["Agent Utilities"],
    # IMPORTANT: The `operation_id` provides a unique, stable identifier for this
    # tool. While optional in FastAPI, it is CRUCIAL for this template as it's
    # used by the pricing system and other integrations. Always define one.
    operation_id="geolocate_city",
)
async def geolocate_city(city: str) -> dict:
    """
    Converts a city name to geographic coordinates.

    This tool is designed specifically for AI agents that need to convert
    user-friendly city names into latitude/longitude pairs for weather queries.
    It is not exposed as a REST endpoint because it's a utility function rather
    than a user-facing feature.
    """
    logger.info(f"Geolocating city: {city}")
    # In a real implementation, you would use a geocoding service.
    # This is a simplified example with hardcoded data.
    city_coords = {
        "London": {"latitude": 51.5074, "longitude": -0.1278},
        "New York": {"latitude": 40.7128, "longitude": -74.0060},
        "Tokyo": {"latitude": 35.6762, "longitude": 139.6503},
    }

    coords = city_coords.get(city, {"latitude": 0.0, "longitude": 0.0})
    return {
        "city": city,
        "latitude": coords["latitude"],
        "longitude": coords["longitude"],
    }

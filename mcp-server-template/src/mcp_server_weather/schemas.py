"""
This module should be changed to match the request and response shapes of your own MCP tools and REST endpoints, while keeping the pattern of small, focused Pydantic models.

Main responsibility: Define shared Pydantic schemas for input and output payloads used across routers and tools.
"""

from typing import Literal

from pydantic import BaseModel, Field


class LocationRequest(BaseModel):
    """Input schema for location-based queries with unit preferences."""

    latitude: str = Field(
        ...,
        pattern=r"^-?\d{1,2}\.\d+$",
        description="Location latitude as a string, e.g., '37.7749'. Format: decimal degrees with optional negative sign",
    )
    longitude: str = Field(
        ...,
        pattern=r"^-?\d{1,3}\.\d+$",
        description="Location longitude as a string, e.g., '-122.4194'. Format: decimal degrees with optional negative sign",
    )
    units: Literal["metric", "imperial"] | None = Field(
        default=None,
        description="Unit system for temperature and other measures: 'metric' or 'imperial'. Defaults to configuration.",
    )

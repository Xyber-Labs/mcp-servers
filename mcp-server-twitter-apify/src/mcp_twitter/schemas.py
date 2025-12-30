"""
This module should be changed to match the request and response shapes of your own MCP tools and REST endpoints, while keeping the pattern of small, focused Pydantic models.

Main responsibility: Define shared Pydantic schemas for input and output payloads used across routers and tools.
"""

from typing import Literal

from pydantic import BaseModel, Field


class TwitterSearchRequest(BaseModel):
    """Input schema for twitter search queries."""

    query: str = Field(
        ...,
        description="Twitter search query or username",
    )
    max_items: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Maximum items to fetch",
    )
    output_format: Literal["min", "max"] | None = Field(
        default="min",
        description="Output format: 'min' or 'max'. Defaults to 'min'.",
    )


class TwitterResponse(BaseModel):
    """Response model for twitter data."""

    items: list[dict] = Field(description="List of twitter items")
    query_id: str = Field(description="Query identifier")
    query_name: str = Field(description="Query name")


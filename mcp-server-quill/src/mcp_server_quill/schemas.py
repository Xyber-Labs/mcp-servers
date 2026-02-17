"""
This module defines shared Pydantic schemas for input and output payloads used across routers and tools.

Main responsibility: Define shared Pydantic schemas for request and response shapes of MCP tools and REST endpoints.
"""

from typing import Any

from pydantic import BaseModel, Field


class TokenSearchResponse(BaseModel):
    """Response model for token search endpoint."""

    address: str = Field(description="Token contract address")
    name: str = Field(description="Token name")
    symbol: str = Field(description="Token symbol")
    chainId: str = Field(description="Chain identifier (e.g., 'ethereum', 'solana')")


class TokenSecurityResponse(BaseModel):
    """Response model for token security analysis endpoints."""

    search_result: TokenSearchResponse = Field(
        description="Token search information including address and basic details"
    )
    quill_data: dict[str, Any] = Field(
        description="Complete security analysis data from QuillCheck API"
    )


class PricingResponse(BaseModel):
    """Response model for pricing configuration."""

    pricing: dict = Field(description="Pricing data for all endpoints")
    message: str | None = Field(
        default=None, description="Optional message about pricing status"
    )


class HealthCheckResponse(BaseModel):
    """Response model for health check endpoint."""

    status: str = Field(description="Server status")

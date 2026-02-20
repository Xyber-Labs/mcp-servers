from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from mcp_twitter.twitter import OutputFormat, SortOrder


class TopicSearchRequest(BaseModel):
    """Request model for topic/keyword search."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "topic": "quantum computing",
                "max_items": 10,
                "sort": "Latest",
                "only_verified": False,
                "only_image": False,
                "lang": "en",
                "output_format": "min",
            }
        }
    )

    topic: str = Field(
        ..., description="Search keyword/topic", examples=["quantum computing"]
    )
    max_items: int = Field(100, ge=1, le=1000, description="Maximum items to fetch")
    sort: SortOrder = Field("Latest", description="Sort order: Latest or Top")
    only_verified: bool = Field(False, description="Only verified users")
    only_image: bool = Field(False, description="Only tweets with images")
    lang: str = Field("en", description="Tweet language code")
    output_format: OutputFormat = Field("min", description="Output format: min or max")


class ProfileSearchRequest(BaseModel):
    """Request model for profile search."""

    username: str = Field(..., description="Twitter username (without @)")
    max_items: int = Field(100, ge=1, le=1000, description="Maximum items to fetch")
    since: date | None = Field(None, description="Start date (YYYY-MM-DD)")
    until: date | None = Field(None, description="End date (YYYY-MM-DD)")
    lang: str = Field("en", description="Tweet language code")
    output_format: OutputFormat = Field("min", description="Output format: min or max")


class ProfileLatestRequest(BaseModel):
    """Request model for latest tweets from a profile (no date range required)."""

    username: str = Field(..., description="Twitter username (without @)")
    max_items: int = Field(10, ge=1, le=1000, description="Maximum items to fetch")
    lang: str = Field("en", description="Tweet language code")
    output_format: OutputFormat = Field("min", description="Output format: min or max")


class RepliesSearchRequest(BaseModel):
    """Request model for replies/conversation search."""

    conversation_id: str = Field(..., description="Twitter conversation ID")
    max_items: int = Field(50, ge=1, le=500, description="Maximum items to fetch")
    lang: str = Field("en", description="Tweet language code")
    output_format: OutputFormat = Field("min", description="Output format: min or max")


class ProfileLatestBatchRequest(BaseModel):
    """Request model for latest tweets from multiple profiles (no date range required)."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "usernames": ["elonmusk", "jack"],
                    "max_items": 10,
                    "lang": "en",
                    "output_format": "min",
                    "continue_on_error": True,
                }
            ]
        }
    )

    usernames: list[str] = Field(
        ..., min_length=1, description="List of Twitter usernames (without @)"
    )
    max_items: int = Field(
        10, ge=1, le=1000, description="Maximum items to fetch per username"
    )
    lang: str = Field("en", description="Tweet language code")
    output_format: OutputFormat = Field("min", description="Output format: min or max")
    continue_on_error: bool = Field(
        True,
        description="If true, return per-username errors and continue. If false, fail the whole request on first error.",
    )


class ProfileBatchSearchRequest(BaseModel):
    """Request model for batch profile search (multiple usernames)."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "usernames": ["elonmusk", "jack"],
                    "max_items": 100,
                    "since": "2025-12-01",
                    "until": "2025-12-31",
                    "lang": "en",
                    "output_format": "min",
                    "continue_on_error": True,
                }
            ]
        }
    )

    usernames: list[str] = Field(
        ..., min_length=1, description="List of Twitter usernames (without @)"
    )
    max_items: int = Field(
        100, ge=1, le=1000, description="Maximum items to fetch per username"
    )
    since: date | None = Field(None, description="Start date (YYYY-MM-DD)")
    until: date | None = Field(None, description="End date (YYYY-MM-DD)")
    lang: str = Field("en", description="Tweet language code")
    output_format: OutputFormat = Field("min", description="Output format: min or max")
    continue_on_error: bool = Field(
        True,
        description="If true, return per-username errors and continue. If false, fail the whole request on first error.",
    )


class ProfileBatchResult(BaseModel):
    """Response model for batch profile search."""

    username: str
    items: list[dict[str, Any]] = Field(default_factory=list)
    error: str | None = None

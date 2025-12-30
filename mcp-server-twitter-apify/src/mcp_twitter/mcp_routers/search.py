"""
This module implements MCP-only search endpoints for Twitter, designed specifically for AI agents.

Main responsibility: Provide search tools that mirror the hybrid router functionality but are
exclusively available to AI agents via MCP. These tools are not exposed as REST endpoints.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

import anyio
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from mcp_twitter.twitter import (
    OutputFormat,
    QueryDefinition,
    SortOrder,
    TwitterScraper,
    create_profile_query,
    create_replies_query,
    create_topic_query,
)

logger = logging.getLogger(__name__)
router = APIRouter()

DEFAULT_TIMEOUT_SECONDS = 600


def _get_scraper(request: Request) -> TwitterScraper:
    """Get scraper from app state."""
    scraper = getattr(request.app.state, "scraper", None)
    if not scraper:
        raise HTTPException(status_code=500, detail="Scraper not initialized")
    return scraper


def _run_query_and_read(temp_scraper: TwitterScraper, query: QueryDefinition) -> list[dict[str, Any]]:
    """Run query and return items directly from scraper (which uses DB cache)."""
    temp_scraper.run_query(query)
    items = temp_scraper.get_last_items()
    if items is None:
        return []
    return [i for i in items if isinstance(i, dict)]


# Request Models (same as hybrid routers)
class TopicSearchRequest(BaseModel):
    """Request model for topic/keyword search."""

    topic: str = Field(..., description="Search keyword/topic")
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


# MCP-only search endpoints
@router.post(
    "/search_topic",
    tags=["Agent Search"],
    operation_id="mcp_search_topic",
    response_model=list[dict[str, Any]],
)
async def search_topic(
    request: TopicSearchRequest,
    http_request: Request,
    timeout_seconds: int = Query(
        DEFAULT_TIMEOUT_SECONDS,
        ge=1,
        le=3600,
        description="Max time to wait for Apify run to finish (seconds).",
    ),
) -> list[dict[str, Any]]:
    """
    Search tweets by topic/keyword (MCP-only).

    This tool searches Twitter for tweets matching a specific topic or keyword.
    It is available exclusively to AI agents via MCP and not exposed as a REST endpoint.
    """
    scraper = _get_scraper(http_request)

    try:
        logger.info(
            "MCP topic search start topic=%r max_items=%s sort=%s verified=%s image=%s lang=%s format=%s timeout=%ss",
            request.topic,
            request.max_items,
            request.sort,
            request.only_verified,
            request.only_image,
            request.lang,
            request.output_format,
            timeout_seconds,
        )
        query = create_topic_query(
            topic=request.topic,
            max_items=request.max_items,
            sort=request.sort,
            only_verified=request.only_verified,
            only_image=request.only_image,
            lang=request.lang,
            output_format=request.output_format,
        )

        temp_scraper = TwitterScraper(
            apify_token=scraper.apify_token,
            results_dir=None,
            actor_name=scraper.actor_id,
            output_format=request.output_format,
            use_cache=True,
        )

        with anyio.fail_after(timeout_seconds):
            items = await anyio.to_thread.run_sync(_run_query_and_read, temp_scraper, query)
        logger.info("MCP topic search done topic=%r items=%d", request.topic, len(items))
        return items
    except Exception as e:
        logger.exception("MCP topic search failed topic=%r error=%s", request.topic, e)
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.post(
    "/search_profile",
    tags=["Agent Search"],
    operation_id="mcp_search_profile",
    response_model=list[dict[str, Any]],
)
async def search_profile(
    request: ProfileSearchRequest,
    http_request: Request,
    timeout_seconds: int = Query(
        DEFAULT_TIMEOUT_SECONDS,
        ge=1,
        le=3600,
        description="Max time to wait for Apify run to finish (seconds).",
    ),
) -> list[dict[str, Any]]:
    """
    Search tweets from a specific user profile (MCP-only).

    This tool searches for tweets from a specific Twitter user within an optional date range.
    It is available exclusively to AI agents via MCP and not exposed as a REST endpoint.
    """
    scraper = _get_scraper(http_request)

    try:
        logger.info(
            "MCP profile search start user=%r max_items=%s since=%r until=%r lang=%s format=%s timeout=%ss",
            request.username,
            request.max_items,
            request.since,
            request.until,
            request.lang,
            request.output_format,
            timeout_seconds,
        )
        query = create_profile_query(
            request.username,
            max_items=request.max_items,
            since=request.since.isoformat() if request.since else None,
            until=request.until.isoformat() if request.until else None,
            lang=request.lang,
        )

        temp_scraper = TwitterScraper(
            apify_token=scraper.apify_token,
            results_dir=None,
            actor_name=scraper.actor_id,
            output_format=request.output_format,
            use_cache=True,
        )

        with anyio.fail_after(timeout_seconds):
            items = await anyio.to_thread.run_sync(_run_query_and_read, temp_scraper, query)
        logger.info("MCP profile search done user=%r items=%d", request.username, len(items))
        return items
    except Exception as e:
        logger.exception("MCP profile search failed user=%r error=%s", request.username, e)
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.post(
    "/search_profile_latest",
    tags=["Agent Search"],
    operation_id="mcp_search_profile_latest",
    response_model=list[dict[str, Any]],
)
async def search_profile_latest(
    request: ProfileLatestRequest,
    http_request: Request,
    timeout_seconds: int = Query(
        DEFAULT_TIMEOUT_SECONDS,
        ge=1,
        le=3600,
        description="Max time to wait for Apify run to finish (seconds).",
    ),
) -> list[dict[str, Any]]:
    """
    Get the latest tweets from a specific user profile (MCP-only).

    This tool retrieves the most recent tweets from a Twitter user without requiring a date range.
    It is available exclusively to AI agents via MCP and not exposed as a REST endpoint.
    """
    scraper = _get_scraper(http_request)

    try:
        logger.info(
            "MCP profile latest start user=%r max_items=%s lang=%s format=%s timeout=%ss",
            request.username,
            request.max_items,
            request.lang,
            request.output_format,
            timeout_seconds,
        )
        query = create_profile_query(
            request.username,
            max_items=request.max_items,
            since=None,
            until=None,
            lang=request.lang,
        )

        temp_scraper = TwitterScraper(
            apify_token=scraper.apify_token,
            results_dir=None,
            actor_name=scraper.actor_id,
            output_format=request.output_format,
            use_cache=True,
        )

        with anyio.fail_after(timeout_seconds):
            items = await anyio.to_thread.run_sync(_run_query_and_read, temp_scraper, query)
        logger.info("MCP profile latest done user=%r items=%d", request.username, len(items))
        return items
    except Exception as e:
        logger.exception("MCP profile latest failed user=%r error=%s", request.username, e)
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.post(
    "/search_replies",
    tags=["Agent Search"],
    operation_id="mcp_search_replies",
    response_model=list[dict[str, Any]],
)
async def search_replies(
    request: RepliesSearchRequest,
    http_request: Request,
    timeout_seconds: int = Query(
        DEFAULT_TIMEOUT_SECONDS,
        ge=1,
        le=3600,
        description="Max time to wait for Apify run to finish (seconds).",
    ),
) -> list[dict[str, Any]]:
    """
    Search replies to a specific tweet conversation (MCP-only).

    This tool retrieves replies to a specific Twitter conversation thread.
    It is available exclusively to AI agents via MCP and not exposed as a REST endpoint.
    """
    scraper = _get_scraper(http_request)

    try:
        logger.info(
            "MCP replies search start conversation_id=%r max_items=%s lang=%s format=%s timeout=%ss",
            request.conversation_id,
            request.max_items,
            request.lang,
            request.output_format,
            timeout_seconds,
        )
        query = create_replies_query(
            conversation_id=request.conversation_id,
            max_items=request.max_items,
            lang=request.lang,
        )

        temp_scraper = TwitterScraper(
            apify_token=scraper.apify_token,
            results_dir=None,
            actor_name=scraper.actor_id,
            output_format=request.output_format,
            use_cache=True,
        )

        with anyio.fail_after(timeout_seconds):
            items = await anyio.to_thread.run_sync(_run_query_and_read, temp_scraper, query)
        logger.info("MCP replies search done conversation_id=%r items=%d", request.conversation_id, len(items))
        return items
    except Exception as e:
        logger.exception("MCP replies search failed conversation_id=%r error=%s", request.conversation_id, e)
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


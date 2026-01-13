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
from pydantic import BaseModel, Field, ConfigDict

from mcp_twitter.twitter import (
    OutputFormat,
    QueryDefinition,
    QueryRegistry,
    QueryType,
    SortOrder,
    TwitterScraper,
    create_profile_query,
    create_replies_query,
    create_topic_query,
)
from mcp_twitter.twitter import scraper as scraper_mod

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

    topic: str = Field(..., description="Search keyword/topic", examples=["quantum computing"])
    max_items: int = Field(20, ge=1, le=1000, description="Maximum items to fetch")
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

    usernames: list[str] = Field(..., min_length=1, description="List of Twitter usernames (without @)")
    max_items: int = Field(100, ge=1, le=1000, description="Maximum items to fetch per username")
    since: date | None = Field(None, description="Start date (YYYY-MM-DD)")
    until: date | None = Field(None, description="End date (YYYY-MM-DD)")
    lang: str = Field("en", description="Tweet language code")
    output_format: OutputFormat = Field("min", description="Output format: min or max")
    continue_on_error: bool = Field(
        True,
        description="If true, return per-username errors and continue. If false, fail the whole request on first error.",
    )


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

    usernames: list[str] = Field(..., min_length=1, description="List of Twitter usernames (without @)")
    max_items: int = Field(10, ge=1, le=1000, description="Maximum items to fetch per username")
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


class QueryTypeInfo(BaseModel):
    """Query type information."""

    type: QueryType
    description: str
    example: str
    preset_count: int


class QueryInfo(BaseModel):
    """Query information."""

    id: str
    type: QueryType
    name: str


def _get_registry(request: Request) -> QueryRegistry:
    """Get registry from app state."""
    registry = getattr(request.app.state, "registry", None)
    if not registry:
        raise HTTPException(status_code=500, detail="Registry not initialized")
    return registry


# MCP-only search endpoints
@router.post(
    "/search_topic",
    tags=["Agent Search"],
    operation_id="twitter_search_topic",
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
        )

        temp_scraper = scraper_mod.TwitterScraper(
            apify_token=scraper.apify_token,
            results_dir=None,
            actor_name=scraper.actor_id,
            output_format=request.output_format,
            use_cache=True,
        )

        items = _run_query_and_read(temp_scraper, query)
        logger.info("MCP topic search done topic=%r items=%d", request.topic, len(items))
        return items
    except Exception as e:
        logger.exception("MCP topic search failed topic=%r error=%s", request.topic, e)
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


# TEMPORARILY DISABLED - keeping only twitter_search_topic enabled
# @router.post(
#     "/search_profile",
#     tags=["Agent Search"],
#     operation_id="twitter_search_profile",
#     response_model=list[dict[str, Any]],
# )
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

        temp_scraper = scraper_mod.TwitterScraper(
            apify_token=scraper.apify_token,
            results_dir=None,
            actor_name=scraper.actor_id,
            output_format=request.output_format,
            use_cache=True,
        )

        items = _run_query_and_read(temp_scraper, query)
        logger.info("MCP profile search done user=%r items=%d", request.username, len(items))
        return items
    except Exception as e:
        logger.exception("MCP profile search failed user=%r error=%s", request.username, e)
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


# TEMPORARILY DISABLED - keeping only twitter_search_topic enabled
# @router.post(
#     "/search_profile_latest",
#     tags=["Agent Search"],
#     operation_id="twitter_search_profile_latest",
#     response_model=list[dict[str, Any]],
# )
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

        temp_scraper = scraper_mod.TwitterScraper(
            apify_token=scraper.apify_token,
            results_dir=None,
            actor_name=scraper.actor_id,
            output_format=request.output_format,
            use_cache=True,
        )

        items = _run_query_and_read(temp_scraper, query)
        logger.info("MCP profile latest done user=%r items=%d", request.username, len(items))
        return items
    except Exception as e:
        logger.exception("MCP profile latest failed user=%r error=%s", request.username, e)
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


# TEMPORARILY DISABLED - keeping only twitter_search_topic enabled
# @router.post(
#     "/search_replies",
#     tags=["Agent Search"],
#     operation_id="twitter_search_replies",
#     response_model=list[dict[str, Any]],
# )
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

        temp_scraper = scraper_mod.TwitterScraper(
            apify_token=scraper.apify_token,
            results_dir=None,
            actor_name=scraper.actor_id,
            output_format=request.output_format,
            use_cache=True,
        )

        items = _run_query_and_read(temp_scraper, query)
        logger.info("MCP replies search done conversation_id=%r items=%d", request.conversation_id, len(items))
        return items
    except Exception as e:
        logger.exception("MCP replies search failed conversation_id=%r error=%s", request.conversation_id, e)
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


# TEMPORARILY DISABLED - keeping only twitter_search_topic enabled
# @router.post(
#     "/search_profile_batch",
#     tags=["Agent Search"],
#     operation_id="twitter_search_profile_batch",
#     response_model=list[ProfileBatchResult],
# )
async def search_profile_batch(
    request: ProfileBatchSearchRequest,
    http_request: Request,
    timeout_seconds: int = Query(
        DEFAULT_TIMEOUT_SECONDS,
        ge=1,
        le=3600,
        description="Max time to wait for the batch to finish (seconds).",
    ),
) -> list[ProfileBatchResult]:
    """
    Search tweets from multiple user profiles in one request (MCP-only).

    This tool searches for tweets from multiple Twitter users within an optional date range.
    It is available exclusively to AI agents via MCP and not exposed as a REST endpoint.
    """
    scraper = _get_scraper(http_request)

    usernames: list[str] = []
    for raw in request.usernames:
        if not raw:
            continue
        parts = [p.strip() for p in raw.split(",")]
        for p in parts:
            if not p:
                continue
            usernames.append(p.lstrip("@").strip())
    if not usernames:
        raise HTTPException(status_code=422, detail="usernames must contain at least one non-empty username")

    temp_scraper = scraper_mod.TwitterScraper(
        apify_token=scraper.apify_token,
        results_dir=None,
        actor_name=scraper.actor_id,
        output_format=request.output_format,
        use_cache=True,
    )

    results: list[ProfileBatchResult] = []
    for username in usernames:
        try:
            logger.info(
                "MCP profile batch item start user=%r max_items=%s since=%r until=%r lang=%s format=%s",
                username,
                request.max_items,
                request.since,
                request.until,
                request.lang,
                request.output_format,
            )
            query = create_profile_query(
                username,
                max_items=request.max_items,
                since=request.since.isoformat() if request.since else None,
                until=request.until.isoformat() if request.until else None,
                lang=request.lang,
            )
            items = _run_query_and_read(temp_scraper, query)
            results.append(ProfileBatchResult(username=username, items=items, error=None))
        except Exception as e:
            logger.exception("MCP profile batch item failed user=%r error=%s", username, e)
            if not request.continue_on_error:
                raise HTTPException(
                    status_code=500,
                    detail=f"Batch search failed for username={username!r}: {str(e)}",
                )
            results.append(ProfileBatchResult(username=username, items=[], error=str(e)))

    return results


# TEMPORARILY DISABLED - keeping only twitter_search_topic enabled
# @router.post(
#     "/search_profile_latest_batch",
#     tags=["Agent Search"],
#     operation_id="twitter_search_profile_latest_batch",
#     response_model=list[ProfileBatchResult],
# )
async def search_profile_latest_batch(
    request: ProfileLatestBatchRequest,
    http_request: Request,
    timeout_seconds: int = Query(
        DEFAULT_TIMEOUT_SECONDS,
        ge=1,
        le=3600,
        description="Max time to wait for the batch to finish (seconds).",
    ),
) -> list[ProfileBatchResult]:
    """
    Get the latest tweets from multiple user profiles in one request (MCP-only).

    This tool retrieves the most recent tweets from multiple Twitter users without requiring a date range.
    It is available exclusively to AI agents via MCP and not exposed as a REST endpoint.
    """
    scraper = _get_scraper(http_request)

    usernames: list[str] = []
    for raw in request.usernames:
        if not raw:
            continue
        parts = [p.strip() for p in raw.split(",")]
        for p in parts:
            if not p:
                continue
            usernames.append(p.lstrip("@").strip())
    if not usernames:
        raise HTTPException(status_code=422, detail="usernames must contain at least one non-empty username")

    temp_scraper = scraper_mod.TwitterScraper(
        apify_token=scraper.apify_token,
        results_dir=None,
        actor_name=scraper.actor_id,
        output_format=request.output_format,
        use_cache=True,
    )

    results: list[ProfileBatchResult] = []
    for username in usernames:
        try:
            logger.info(
                "MCP profile latest batch item start user=%r max_items=%s lang=%s format=%s",
                username,
                request.max_items,
                request.lang,
                request.output_format,
            )
            query = create_profile_query(
                username,
                max_items=request.max_items,
                since=None,
                until=None,
                lang=request.lang,
            )
            items = _run_query_and_read(temp_scraper, query)
            results.append(ProfileBatchResult(username=username, items=items, error=None))
        except Exception as e:
            logger.exception("MCP profile latest batch item failed user=%r error=%s", username, e)
            if not request.continue_on_error:
                raise HTTPException(
                    status_code=500,
                    detail=f"Batch latest search failed for username={username!r}: {str(e)}",
                )
            results.append(ProfileBatchResult(username=username, items=[], error=str(e)))

    return results


# TEMPORARILY DISABLED - keeping only twitter_search_topic enabled
# @router.post(
#     "/run_query/{query_id}",
#     tags=["Agent Search"],
#     operation_id="twitter_run_query",
#     response_model=list[dict[str, Any]],
# )
async def run_query(
    query_id: str,
    http_request: Request,
    timeout_seconds: int = Query(
        DEFAULT_TIMEOUT_SECONDS,
        ge=1,
        le=3600,
        description="Max time to wait for Apify run to finish (seconds).",
    ),
) -> list[dict[str, Any]]:
    """
    Run a predefined query by ID (MCP-only).

    This tool runs a predefined query from the registry by its ID.
    It is available exclusively to AI agents via MCP and not exposed as a REST endpoint.
    """
    registry = _get_registry(http_request)
    scraper = _get_scraper(http_request)

    query = registry.get(query_id)
    if not query:
        raise HTTPException(status_code=404, detail=f"Query '{query_id}' not found")

    try:
        logger.info("MCP preset run start id=%s type=%s name=%r timeout=%ss", query.id, query.type, query.name, timeout_seconds)
        items = await anyio.to_thread.run_sync(_run_query_and_read, scraper, query)
        logger.info("MCP preset run done id=%s items=%d", query.id, len(items))
        return items
    except Exception as e:
        logger.exception("MCP preset run failed id=%s error=%s", query_id, e)
        raise HTTPException(status_code=500, detail=f"Query execution failed: {str(e)}")


# TEMPORARILY DISABLED - keeping only twitter_search_topic enabled
# @router.get(
#     "/list_types",
#     tags=["Agent Queries"],
#     operation_id="twitter_list_types",
#     response_model=list[QueryTypeInfo],
# )
async def list_types(http_request: Request) -> list[QueryTypeInfo]:
    """
    List all available query types with descriptions (MCP-only).

    This tool provides information about available query types and their capabilities.
    It is available exclusively to AI agents via MCP and not exposed as a REST endpoint.
    """
    registry = _get_registry(http_request)

    descriptions: dict[str, str] = {
        "topic": "Search tweets by keyword/topic (supports sort Top/Latest, verified/image filters)",
        "profile": "Search tweets from a specific username (supports date range filters)",
        "replies": "Fetch replies for a thread via conversation_id",
    }
    examples: dict[str, str] = {
        "topic": 'POST /search_topic {"topic": "starlink", "sort": "Top", "max_items": 10}',
        "profile": 'POST /search_profile {"username": "elonmusk", "max_items": 100}',
        "replies": 'POST /search_replies {"conversation_id": "1728108619189874825"}',
    }

    return [
        QueryTypeInfo(
            type=q_type,
            description=descriptions.get(q_type, ""),
            example=examples.get(q_type, ""),
            preset_count=len(registry.by_type(q_type)),
        )
        for q_type in registry.types()
    ]


# TEMPORARILY DISABLED - keeping only twitter_search_topic enabled
# @router.get(
#     "/list_queries",
#     tags=["Agent Queries"],
#     operation_id="twitter_list_queries",
#     response_model=list[QueryInfo],
# )
async def list_queries(
    http_request: Request,
    query_type: QueryType | None = Query(None, description="Filter by query type"),
) -> list[QueryInfo]:
    """
    List all available queries, optionally filtered by type (MCP-only).

    This tool provides information about available predefined queries.
    It is available exclusively to AI agents via MCP and not exposed as a REST endpoint.
    """
    registry = _get_registry(http_request)

    queries = registry.list_queries(query_type=query_type)
    return [
        QueryInfo(id=q.id, type=q.type, name=q.name) for q in queries
    ]


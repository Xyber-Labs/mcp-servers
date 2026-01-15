"""
This module implements hybrid (REST + MCP) endpoints for Twitter search operations.

Main responsibility: Provide search endpoints that are available to both REST API consumers and AI agents via MCP.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field

from mcp_twitter.twitter import (
    OutputFormat,
    QueryDefinition,
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


# Request Models
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

    usernames: list[str] = Field(..., min_length=1, description="List of Twitter usernames (without @)")
    max_items: int = Field(10, ge=1, le=1000, description="Maximum items to fetch per username")
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


class ProfileBatchResult(BaseModel):
    """Response model for batch profile search."""

    username: str
    items: list[dict[str, Any]] = Field(default_factory=list)
    error: str | None = None


# Routes
@router.post(
    "/v1/search/topic",
    tags=["Search"],
    operation_id="search_topic",
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
    """Search tweets by topic/keyword."""
    scraper = _get_scraper(http_request)
    
    try:
        logger.info(
            "topic search start topic=%r sort=%s max_items=%s verified=%s image=%s lang=%s format=%s timeout=%ss",
            request.topic,
            request.sort,
            request.max_items,
            request.only_verified,
            request.only_image,
            request.lang,
            request.output_format,
            timeout_seconds,
        )
        query = create_topic_query(
            request.topic,
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

        items = await asyncio.wait_for(
            asyncio.to_thread(_run_query_and_read, temp_scraper, query),
            timeout=timeout_seconds,
        )
        logger.info("topic search done topic=%r items=%d", request.topic, len(items))
        return items
    except asyncio.TimeoutError:
        logger.error("topic search timeout topic=%r timeout=%ss", request.topic, timeout_seconds)
        raise HTTPException(status_code=504, detail=f"Search timed out after {timeout_seconds} seconds")
    except Exception as e:
        logger.exception("topic search failed topic=%r error=%s", request.topic, e)
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}") from e


@router.post(
    "/v1/search/profile",
    tags=["Search"],
    operation_id="search_profile",
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
    """Search tweets from a specific user profile."""
    scraper = _get_scraper(http_request)
    
    try:
        logger.info(
            "profile search start user=%r max_items=%s since=%r until=%r lang=%s format=%s timeout=%ss",
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

        items = await asyncio.wait_for(
            asyncio.to_thread(_run_query_and_read, temp_scraper, query),
            timeout=timeout_seconds,
        )
        logger.info("profile search done user=%r items=%d", request.username, len(items))
        return items
    except asyncio.TimeoutError:
        logger.error("profile search timeout user=%r timeout=%ss", request.username, timeout_seconds)
        raise HTTPException(status_code=504, detail=f"Search timed out after {timeout_seconds} seconds")
    except Exception as e:
        logger.exception("profile search failed user=%r error=%s", request.username, e)
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}") from e


@router.post(
    "/v1/search/profile/latest",
    tags=["Search"],
    operation_id="search_profile_latest",
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
    """Get the latest tweets from a specific user profile."""
    scraper = _get_scraper(http_request)

    try:
        logger.info(
            "profile latest start user=%r max_items=%s lang=%s format=%s timeout=%ss",
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

        items = await asyncio.wait_for(
            asyncio.to_thread(_run_query_and_read, temp_scraper, query),
            timeout=timeout_seconds,
        )
        logger.info("profile latest done user=%r items=%d", request.username, len(items))
        return items
    except asyncio.TimeoutError:
        logger.error("profile latest timeout user=%r timeout=%ss", request.username, timeout_seconds)
        raise HTTPException(status_code=504, detail=f"Search timed out after {timeout_seconds} seconds")
    except Exception as e:
        logger.exception("profile latest failed user=%r error=%s", request.username, e)
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}") from e


@router.post(
    "/v1/search/replies",
    tags=["Search"],
    operation_id="search_replies",
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
    """Search replies for a conversation thread."""
    scraper = _get_scraper(http_request)
    
    try:
        logger.info(
            "replies search start conversation_id=%r max_items=%s lang=%s format=%s timeout=%ss",
            request.conversation_id,
            request.max_items,
            request.lang,
            request.output_format,
            timeout_seconds,
        )
        query = create_replies_query(
            request.conversation_id,
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

        items = await asyncio.wait_for(
            asyncio.to_thread(_run_query_and_read, temp_scraper, query),
            timeout=timeout_seconds,
        )
        logger.info(
            "replies search done conversation_id=%r items=%d",
            request.conversation_id,
            len(items),
        )
        return items
    except asyncio.TimeoutError:
        logger.error("replies search timeout conversation_id=%r timeout=%ss", request.conversation_id, timeout_seconds)
        raise HTTPException(status_code=504, detail=f"Search timed out after {timeout_seconds} seconds")
    except Exception as e:
        logger.exception("replies search failed conversation_id=%r error=%s", request.conversation_id, e)
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}") from e


@router.post(
    "/v1/search/profile/batch",
    tags=["Search"],
    operation_id="search_profile_batch",
    response_model=list[ProfileBatchResult],
)
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
    """Search tweets from multiple user profiles in one request (looping per username)."""
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
    # Calculate timeout per username (distribute total timeout across all usernames)
    timeout_per_username = max(1, timeout_seconds // len(usernames)) if usernames else timeout_seconds
    
    for username in usernames:
        try:
            logger.info(
                "profile batch item start user=%r max_items=%s since=%r until=%r lang=%s format=%s timeout=%ss",
                username,
                request.max_items,
                request.since,
                request.until,
                request.lang,
                request.output_format,
                timeout_per_username,
            )
            query = create_profile_query(
                username,
                max_items=request.max_items,
                since=request.since.isoformat() if request.since else None,
                until=request.until.isoformat() if request.until else None,
                lang=request.lang,
            )
            items = await asyncio.wait_for(
                asyncio.to_thread(_run_query_and_read, temp_scraper, query),
                timeout=timeout_per_username,
            )
            results.append(ProfileBatchResult(username=username, items=items, error=None))
        except asyncio.TimeoutError:
            logger.error("profile batch item timeout user=%r timeout=%ss", username, timeout_per_username)
            if not request.continue_on_error:
                raise HTTPException(
                    status_code=504,
                    detail=f"Batch search timed out for username={username!r} after {timeout_per_username} seconds",
                )
            results.append(ProfileBatchResult(username=username, items=[], error=f"Timeout after {timeout_per_username} seconds"))
        except Exception as e:
            logger.exception("profile batch item failed user=%r error=%s", username, e)
            if not request.continue_on_error:
                raise HTTPException(
                    status_code=500,
                    detail=f"Batch search failed for username={username!r}: {str(e)}",
                ) from e
            results.append(ProfileBatchResult(username=username, items=[], error=str(e)))

    return results


@router.post(
    "/v1/search/profile/latest/batch",
    tags=["Search"],
    operation_id="search_profile_latest_batch",
    response_model=list[ProfileBatchResult],
)
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
    """Get the latest tweets from multiple user profiles in one request (looping per username)."""
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
    # Calculate timeout per username (distribute total timeout across all usernames)
    timeout_per_username = max(1, timeout_seconds // len(usernames)) if usernames else timeout_seconds
    
    for username in usernames:
        try:
            logger.info(
                "profile latest batch item start user=%r max_items=%s lang=%s format=%s timeout=%ss",
                username,
                request.max_items,
                request.lang,
                request.output_format,
                timeout_per_username,
            )
            query = create_profile_query(
                username,
                max_items=request.max_items,
                since=None,
                until=None,
                lang=request.lang,
            )
            items = await asyncio.wait_for(
                asyncio.to_thread(_run_query_and_read, temp_scraper, query),
                timeout=timeout_per_username,
            )
            results.append(ProfileBatchResult(username=username, items=items, error=None))
        except asyncio.TimeoutError:
            logger.error("profile latest batch item timeout user=%r timeout=%ss", username, timeout_per_username)
            if not request.continue_on_error:
                raise HTTPException(
                    status_code=504,
                    detail=f"Batch latest search timed out for username={username!r} after {timeout_per_username} seconds",
                )
            results.append(ProfileBatchResult(username=username, items=[], error=f"Timeout after {timeout_per_username} seconds"))
        except Exception as e:
            logger.exception("profile latest batch item failed user=%r error=%s", username, e)
            if not request.continue_on_error:
                raise HTTPException(
                    status_code=500,
                    detail=f"Batch latest search failed for username={username!r}: {str(e)}",
                ) from e
            results.append(ProfileBatchResult(username=username, items=[], error=str(e)))

    return results


@router.post(
    "/v1/run/{query_id}",
    tags=["Search"],
    operation_id="run_query",
    response_model=list[dict[str, Any]],
)
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
    """Run a predefined query by ID."""
    registry = getattr(http_request.app.state, "registry", None)
    scraper = _get_scraper(http_request)
    
    if not registry:
        raise HTTPException(status_code=500, detail="Registry not initialized")
    
    query = registry.get(query_id)
    if not query:
        raise HTTPException(status_code=404, detail=f"Query '{query_id}' not found")
    
    try:
        logger.info("preset run start id=%s type=%s name=%r timeout=%ss", query.id, query.type, query.name, timeout_seconds)
        items = await asyncio.wait_for(
            asyncio.to_thread(_run_query_and_read, scraper, query),
            timeout=timeout_seconds,
        )
        logger.info("preset run done id=%s items=%d", query.id, len(items))
        return items
    except asyncio.TimeoutError:
        logger.error("preset run timeout id=%s timeout=%ss", query_id, timeout_seconds)
        raise HTTPException(status_code=504, detail=f"Query execution timed out after {timeout_seconds} seconds")
    except Exception as e:
        logger.exception("preset run failed id=%s error=%s", query_id, e)
        raise HTTPException(status_code=500, detail=f"Query execution failed: {str(e)}") from e


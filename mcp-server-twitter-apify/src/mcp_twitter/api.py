"""
FastAPI REST API for Twitter scraper service.

Swagger docs available at /docs
"""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path
from typing import Any, AsyncGenerator

import anyio
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from mcp_twitter.config import AppSettings
from mcp_twitter.logger import get_logger
from mcp_twitter.models import OutputFormat, QueryDefinition, QueryType, SortOrder
from mcp_twitter.queries import (
    build_default_registry,
    create_profile_query,
    create_replies_query,
    create_topic_query,
)
from mcp_twitter.registry import QueryRegistry
from mcp_twitter.scraper import TwitterScraper

# Global registry and scraper (initialized on startup)
registry: QueryRegistry | None = None
scraper: TwitterScraper | None = None
log = get_logger("mcp_twitter.api")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Initialize registry and scraper on API startup."""
    global registry, scraper
    registry = build_default_registry()
    
    settings = AppSettings()
    token = settings.apify.apify_token
    if not token:
        raise RuntimeError("APIFY_TOKEN not configured. Set it in .env or environment.")
    
    actor_name = settings.apify.actor_name
    scraper = TwitterScraper(
        apify_token=token,
        results_dir=None,  # Disable file-based storage, use DB cache only
        actor_name=actor_name,  # Use configured actor_name
        output_format="min",
        use_cache=True,  # Enable database cache
    )
    
    print(f"🔧 Initialized with actor: {actor_name}")
    try:
        from db import get_db_instance
        db = get_db_instance()
        print(f"✅ Database cache enabled")
    except Exception as e:
        print(f"⚠️  Database cache not available: {e}")
    
    yield  # App runs here
    
    # Cleanup (if needed)
    pass


app = FastAPI(
    title="Twitter Scraper API",
    description="REST API for searching Twitter via Apify apidojo/twitter-scraper-lite",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

DEFAULT_TIMEOUT_SECONDS = 600


def _run_query_and_read(temp_scraper: TwitterScraper, query: QueryDefinition) -> list[dict[str, Any]]:
    """
    Run query and return items directly from scraper (which uses DB cache).
    
    The scraper now stores items in _last_items after running, so we can access them directly.
    """
    temp_scraper.run_query(query)
    items = temp_scraper.get_last_items()
    if items is None:
        return []
    # Ensure consistent response type for FastAPI schema
    return [i for i in items if isinstance(i, dict)]


# Request/Response Models
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


class RepliesSearchRequest(BaseModel):
    """Request model for replies/conversation search."""

    conversation_id: str = Field(..., description="Twitter conversation ID")
    max_items: int = Field(50, ge=1, le=500, description="Maximum items to fetch")
    lang: str = Field("en", description="Tweet language code")
    output_format: OutputFormat = Field("min", description="Output format: min or max")


class SearchResponse(BaseModel):
    """Response model for search operations."""

    success: bool
    query_id: str
    query_name: str
    query_type: QueryType
    output_file: str
    items_count: int
    message: str


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


# API Routes
@app.get("/api/v1/types", response_model=list[QueryTypeInfo])
async def list_types() -> list[QueryTypeInfo]:
    """List all available query types with descriptions."""
    if not registry:
        raise HTTPException(status_code=500, detail="Registry not initialized")
    
    descriptions: dict[str, str] = {
        "topic": "Search tweets by keyword/topic (supports sort Top/Latest, verified/image filters)",
        "profile": "Search tweets from a specific username (supports date range filters)",
        "replies": "Fetch replies for a thread via conversation_id",
    }
    examples: dict[str, str] = {
        "topic": 'POST /api/v1/search/topic {"topic": "starlink", "sort": "Top", "max_items": 50}',
        "profile": 'POST /api/v1/search/profile {"username": "elonmusk", "max_items": 100}',
        "replies": 'POST /api/v1/search/replies {"conversation_id": "1728108619189874825"}',
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


@app.get("/api/v1/queries", response_model=list[QueryInfo])
async def list_queries(
    query_type: QueryType | None = Query(None, description="Filter by query type")
) -> list[QueryInfo]:
    """List all available queries, optionally filtered by type."""
    if not registry:
        raise HTTPException(status_code=500, detail="Registry not initialized")
    
    queries = registry.list_queries(query_type=query_type)
    return [
        QueryInfo(id=q.id, type=q.type, name=q.name) for q in queries
    ]


@app.post("/api/v1/search/topic", response_model=list[dict[str, Any]])
async def search_topic(
    request: TopicSearchRequest,
    timeout_seconds: int = Query(
        DEFAULT_TIMEOUT_SECONDS,
        ge=1,
        le=3600,
        description="Max time to wait for Apify run to finish (seconds).",
    ),
) -> list[dict[str, Any]]:
    """Search tweets by topic/keyword."""
    if not scraper:
        raise HTTPException(status_code=500, detail="Scraper not initialized")
    
    try:
        log.info(
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
        
        # Create a temporary scraper with requested output format
        temp_scraper = TwitterScraper(
            apify_token=scraper.apify_token,
            results_dir=None,  # Use DB cache only
            actor_name=scraper.actor_id,  # actor_id stores the actor name value
            output_format=request.output_format,
            use_cache=True,
        )
        
        with anyio.fail_after(timeout_seconds):
            items = await anyio.to_thread.run_sync(_run_query_and_read, temp_scraper, query)
        log.info("topic search done topic=%r items=%d", request.topic, len(items))
        return items
    except Exception as e:
        log.exception("topic search failed topic=%r error=%s", request.topic, e)
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@app.post("/api/v1/search/profile", response_model=list[dict[str, Any]])
async def search_profile(
    request: ProfileSearchRequest,
    timeout_seconds: int = Query(
        DEFAULT_TIMEOUT_SECONDS,
        ge=1,
        le=3600,
        description="Max time to wait for Apify run to finish (seconds).",
    ),
) -> list[dict[str, Any]]:
    """Search tweets from a specific user profile."""
    if not scraper:
        raise HTTPException(status_code=500, detail="Scraper not initialized")
    
    try:
        log.info(
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
        
        temp_scraper = TwitterScraper(
            apify_token=scraper.apify_token,
            results_dir=None,  # Use DB cache only
            actor_name=scraper.actor_id,  # actor_id stores the actor name value
            output_format=request.output_format,
            use_cache=True,
        )

        with anyio.fail_after(timeout_seconds):
            items = await anyio.to_thread.run_sync(_run_query_and_read, temp_scraper, query)
        log.info("profile search done user=%r items=%d", request.username, len(items))
        return items
    except Exception as e:
        log.exception("profile search failed user=%r error=%s", request.username, e)
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@app.post("/api/v1/search/profile/batch", response_model=list[ProfileBatchResult])
async def search_profile_batch(
    request: ProfileBatchSearchRequest,
    timeout_seconds: int = Query(
        DEFAULT_TIMEOUT_SECONDS,
        ge=1,
        le=3600,
        description="Max time to wait for the batch to finish (seconds).",
    ),
) -> list[ProfileBatchResult]:
    """Search tweets from multiple user profiles in one request (looping per username)."""
    if not scraper:
        raise HTTPException(status_code=500, detail="Scraper not initialized")

    usernames: list[str] = []
    for raw in request.usernames:
        if not raw:
            continue
        # Allow comma-separated usernames inside a single list item (common copy/paste pattern).
        parts = [p.strip() for p in raw.split(",")]
        for p in parts:
            if not p:
                continue
            usernames.append(p.lstrip("@").strip())
    if not usernames:
        raise HTTPException(status_code=422, detail="usernames must contain at least one non-empty username")

    temp_scraper = TwitterScraper(
        apify_token=scraper.apify_token,
        results_dir=None,  # Use DB cache only
        actor_name=scraper.actor_id,  # actor_id stores the actor name value
        output_format=request.output_format,
        use_cache=True,
    )

    results: list[ProfileBatchResult] = []
    with anyio.fail_after(timeout_seconds):
        for username in usernames:
            try:
                log.info(
                    "profile batch item start user=%r max_items=%s since=%r until=%r lang=%s format=%s",
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
                items = await anyio.to_thread.run_sync(_run_query_and_read, temp_scraper, query)
                results.append(ProfileBatchResult(username=username, items=items, error=None))
            except Exception as e:
                log.exception("profile batch item failed user=%r error=%s", username, e)
                if not request.continue_on_error:
                    raise HTTPException(
                        status_code=500,
                        detail=f"Batch search failed for username={username!r}: {str(e)}",
                    )
                results.append(ProfileBatchResult(username=username, items=[], error=str(e)))

    return results


@app.post("/api/v1/search/profile/latest/batch", response_model=list[ProfileBatchResult])
async def search_profile_latest_batch(
    request: ProfileLatestBatchRequest,
    timeout_seconds: int = Query(
        DEFAULT_TIMEOUT_SECONDS,
        ge=1,
        le=3600,
        description="Max time to wait for the batch to finish (seconds).",
    ),
) -> list[ProfileBatchResult]:
    """Get the latest tweets from multiple user profiles in one request (looping per username)."""
    if not scraper:
        raise HTTPException(status_code=500, detail="Scraper not initialized")

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

    temp_scraper = TwitterScraper(
        apify_token=scraper.apify_token,
        results_dir=None,  # Use DB cache only
        actor_name=scraper.actor_id,  # actor_id stores the actor name value
        output_format=request.output_format,
        use_cache=True,
    )

    results: list[ProfileBatchResult] = []
    with anyio.fail_after(timeout_seconds):
        for username in usernames:
            try:
                log.info(
                    "profile latest batch item start user=%r max_items=%s lang=%s format=%s",
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
                items = await anyio.to_thread.run_sync(_run_query_and_read, temp_scraper, query)
                results.append(ProfileBatchResult(username=username, items=items, error=None))
            except Exception as e:
                log.exception("profile latest batch item failed user=%r error=%s", username, e)
                if not request.continue_on_error:
                    raise HTTPException(
                        status_code=500,
                        detail=f"Batch latest search failed for username={username!r}: {str(e)}",
                    )
                results.append(ProfileBatchResult(username=username, items=[], error=str(e)))

    return results


@app.post("/api/v1/search/profile/latest", response_model=list[dict[str, Any]])
async def search_profile_latest(
    request: ProfileLatestRequest,
    timeout_seconds: int = Query(
        DEFAULT_TIMEOUT_SECONDS,
        ge=1,
        le=3600,
        description="Max time to wait for Apify run to finish (seconds).",
    ),
) -> list[dict[str, Any]]:
    """Get the latest tweets from a specific user profile."""
    if not scraper:
        raise HTTPException(status_code=500, detail="Scraper not initialized")

    try:
        log.info(
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

        temp_scraper = TwitterScraper(
            apify_token=scraper.apify_token,
            results_dir=None,  # Use DB cache only
            actor_name=scraper.actor_id,  # actor_id stores the actor name value
            output_format=request.output_format,
            use_cache=True,
        )

        with anyio.fail_after(timeout_seconds):
            items = await anyio.to_thread.run_sync(_run_query_and_read, temp_scraper, query)
        log.info("profile latest done user=%r items=%d", request.username, len(items))
        return items
    except Exception as e:
        log.exception("profile latest failed user=%r error=%s", request.username, e)
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@app.post("/api/v1/search/replies", response_model=list[dict[str, Any]])
async def search_replies(
    request: RepliesSearchRequest,
    timeout_seconds: int = Query(
        DEFAULT_TIMEOUT_SECONDS,
        ge=1,
        le=3600,
        description="Max time to wait for Apify run to finish (seconds).",
    ),
) -> list[dict[str, Any]]:
    """Search replies for a conversation thread."""
    if not scraper:
        raise HTTPException(status_code=500, detail="Scraper not initialized")
    
    try:
        log.info(
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
        
        temp_scraper = TwitterScraper(
            apify_token=scraper.apify_token,
            results_dir=None,  # Use DB cache only
            actor_name=scraper.actor_id,  # actor_id stores the actor name value
            output_format=request.output_format,
            use_cache=True,
        )

        with anyio.fail_after(timeout_seconds):
            items = await anyio.to_thread.run_sync(_run_query_and_read, temp_scraper, query)
        log.info(
            "replies search done conversation_id=%r items=%d",
            request.conversation_id,
            len(items),
        )
        return items
    except Exception as e:
        log.exception("replies search failed conversation_id=%r error=%s", request.conversation_id, e)
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@app.post("/api/v1/run/{query_id}", response_model=list[dict[str, Any]])
async def run_query(
    query_id: str,
    timeout_seconds: int = Query(
        DEFAULT_TIMEOUT_SECONDS,
        ge=1,
        le=3600,
        description="Max time to wait for Apify run to finish (seconds).",
    ),
) -> list[dict[str, Any]]:
    """Run a predefined query by ID."""
    if not registry or not scraper:
        raise HTTPException(status_code=500, detail="Registry/Scraper not initialized")
    
    query = registry.get(query_id)
    if not query:
        raise HTTPException(status_code=404, detail=f"Query '{query_id}' not found")
    
    try:
        log.info("preset run start id=%s type=%s name=%r timeout=%ss", query.id, query.type, query.name, timeout_seconds)
        with anyio.fail_after(timeout_seconds):
            items = await anyio.to_thread.run_sync(_run_query_and_read, scraper, query)
        log.info("preset run done id=%s items=%d", query.id, len(items))
        return items
    except Exception as e:
        log.exception("preset run failed id=%s error=%s", query_id, e)
        raise HTTPException(status_code=500, detail=f"Query execution failed: {str(e)}")


@app.get("/api/v1/results/{filename}", response_model=None)
async def get_results(filename: str) -> JSONResponse:
    """
    Get saved search results by query key (deprecated: use search endpoints directly).
    
    This endpoint is kept for backward compatibility but results are now stored in DB.
    """
    # Try to extract query key from filename or return empty
    # In practice, users should use the search endpoints directly
    raise HTTPException(
        status_code=410,
        detail="File-based results are deprecated. Use search endpoints directly to access cached results.",
    )


@app.get("/api/v1/results")
async def list_results() -> dict[str, str | bool]:
    """
    List cache status (deprecated: file listing no longer supported).
    
    Results are now stored in Postgres database cache.
    """
    return {
        "message": "File-based results are deprecated. Results are cached in Postgres database.",
        "cache_enabled": scraper.use_cache if scraper else False,
    }


@app.get("/")
async def root() -> dict[str, str]:
    """API root endpoint."""
    return {
        "service": "Twitter Scraper API",
        "version": "2.0.0",
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/health",
    }


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy", "service": "twitter-scraper-api"}


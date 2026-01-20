"""
This module implements REST-only endpoints for query management.

Main responsibility: Provide endpoints for listing query types and queries that are only available via REST API.
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from mcp_twitter.twitter import QueryRegistry, QueryType

logger = logging.getLogger(__name__)
router = APIRouter()


def _get_registry(request: Request) -> QueryRegistry:
    """Get registry from app state."""
    registry = getattr(request.app.state, "registry", None)
    if not registry:
        raise HTTPException(status_code=500, detail="Registry not initialized")
    return registry


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


@router.get(
    "/v1/types",
    tags=["Queries"],
    operation_id="list_types",
    response_model=list[QueryTypeInfo],
)
async def list_types(http_request: Request) -> list[QueryTypeInfo]:
    """List all available query types with descriptions."""
    registry = _get_registry(http_request)
    
    descriptions: dict[str, str] = {
        "topic": "Search tweets by keyword/topic (supports sort Top/Latest, verified/image filters)",
        "profile": "Search tweets from a specific username (supports date range filters)",
        "replies": "Fetch replies for a thread via conversation_id",
    }
    examples: dict[str, str] = {
        "topic": 'POST /hybrid/v1/search/topic {"topic": "starlink", "sort": "Top", "max_items": 10}',
        "profile": 'POST /hybrid/v1/search/profile {"username": "elonmusk", "max_items": 100}',
        "replies": 'POST /hybrid/v1/search/replies {"conversation_id": "1728108619189874825"}',
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


@router.get(
    "/v1/queries",
    tags=["Queries"],
    operation_id="list_queries",
    response_model=list[QueryInfo],
)
async def list_queries(
    http_request: Request,
    query_type: QueryType | None = Query(None, description="Filter by query type"),
) -> list[QueryInfo]:
    """List all available queries, optionally filtered by type."""
    registry = _get_registry(http_request)
    
    queries = registry.list_queries(query_type=query_type)
    return [
        QueryInfo(id=q.id, type=q.type, name=q.name) for q in queries
    ]


@router.get(
    "/v1/results/{filename}",
    tags=["Queries"],
    operation_id="get_results",
)
async def get_results(filename: str, http_request: Request) -> dict[str, str]:
    """
    Get saved search results by query key (deprecated: use search endpoints directly).
    
    This endpoint is kept for backward compatibility but results are now stored in DB.
    """
    raise HTTPException(
        status_code=410,
        detail="File-based results are deprecated. Use search endpoints directly to access cached results.",
    )


@router.get(
    "/v1/results",
    tags=["Queries"],
    operation_id="list_results",
)
async def list_results(http_request: Request) -> dict[str, str | bool]:
    """
    List cache status (deprecated: file listing no longer supported).
    
    Results are now stored in Postgres database cache.
    """
    scraper = getattr(http_request.app.state, "scraper", None)
    return {
        "message": "File-based results are deprecated. Results are cached in Postgres database.",
        "cache_enabled": scraper.use_cache if scraper else False,
    }


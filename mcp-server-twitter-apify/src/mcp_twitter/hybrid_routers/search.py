from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from mcp_twitter.dependencies import get_scraper
from mcp_twitter.schemas import (
    ProfileBatchResult,
    ProfileBatchSearchRequest,
    ProfileLatestBatchRequest,
    ProfileLatestRequest,
    ProfileSearchRequest,
    RepliesSearchRequest,
    TopicSearchRequest,
)
from mcp_twitter.twitter import (
    QueryDefinition,
    TwitterScraper,
    create_profile_query,
    create_replies_query,
    create_topic_query,
)
from mcp_twitter.twitter import scraper as scraper_mod

logger = logging.getLogger(__name__)
router = APIRouter()

DEFAULT_TIMEOUT_SECONDS = 600


def _run_query_and_read(
    temp_scraper: TwitterScraper, query: QueryDefinition
) -> list[dict[str, Any]]:
    """Run query and return items directly from scraper (which uses DB cache)."""
    temp_scraper.run_query(query)
    items = temp_scraper.get_last_items()
    if items is None:
        return []
    return [i for i in items if isinstance(i, dict)]


# Routes
@router.post(
    "/v1/search/topic",
    tags=["Search"],
    operation_id="search_topic",
    response_model=list[dict[str, Any]],
)
async def search_topic(
    request: TopicSearchRequest,
    scraper: TwitterScraper = Depends(get_scraper),
    timeout_seconds: int = Query(
        DEFAULT_TIMEOUT_SECONDS,
        ge=1,
        le=3600,
        description="Max time to wait for Apify run to finish (seconds).",
    ),
) -> list[dict[str, Any]]:
    """Search tweets by topic/keyword."""
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
            actor_name=scraper.actor_id,
            output_format=request.output_format,
            database=scraper._db,
        )

        items = await asyncio.wait_for(
            asyncio.to_thread(_run_query_and_read, temp_scraper, query),
            timeout=timeout_seconds,
        )
        logger.info("topic search done topic=%r items=%d", request.topic, len(items))
        return items
    except TimeoutError:
        logger.error(
            "topic search timeout topic=%r timeout=%ss", request.topic, timeout_seconds
        )
        raise HTTPException(
            status_code=504, detail=f"Search timed out after {timeout_seconds} seconds"
        )
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
    scraper: TwitterScraper = Depends(get_scraper),
    timeout_seconds: int = Query(
        DEFAULT_TIMEOUT_SECONDS,
        ge=1,
        le=3600,
        description="Max time to wait for Apify run to finish (seconds).",
    ),
) -> list[dict[str, Any]]:
    """Search tweets from a specific user profile."""
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
            actor_name=scraper.actor_id,
            output_format=request.output_format,
            database=scraper._db,
        )

        items = await asyncio.wait_for(
            asyncio.to_thread(_run_query_and_read, temp_scraper, query),
            timeout=timeout_seconds,
        )
        logger.info(
            "profile search done user=%r items=%d", request.username, len(items)
        )
        return items
    except TimeoutError:
        logger.error(
            "profile search timeout user=%r timeout=%ss",
            request.username,
            timeout_seconds,
        )
        raise HTTPException(
            status_code=504, detail=f"Search timed out after {timeout_seconds} seconds"
        )
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
    scraper: TwitterScraper = Depends(get_scraper),
    timeout_seconds: int = Query(
        DEFAULT_TIMEOUT_SECONDS,
        ge=1,
        le=3600,
        description="Max time to wait for Apify run to finish (seconds).",
    ),
) -> list[dict[str, Any]]:
    """Get the latest tweets from a specific user profile."""
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
            actor_name=scraper.actor_id,
            output_format=request.output_format,
            database=scraper._db,
        )

        items = await asyncio.wait_for(
            asyncio.to_thread(_run_query_and_read, temp_scraper, query),
            timeout=timeout_seconds,
        )
        logger.info(
            "profile latest done user=%r items=%d", request.username, len(items)
        )
        return items
    except TimeoutError:
        logger.error(
            "profile latest timeout user=%r timeout=%ss",
            request.username,
            timeout_seconds,
        )
        raise HTTPException(
            status_code=504, detail=f"Search timed out after {timeout_seconds} seconds"
        )
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
    scraper: TwitterScraper = Depends(get_scraper),
    timeout_seconds: int = Query(
        DEFAULT_TIMEOUT_SECONDS,
        ge=1,
        le=3600,
        description="Max time to wait for Apify run to finish (seconds).",
    ),
) -> list[dict[str, Any]]:
    """Search replies for a conversation thread."""
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
            actor_name=scraper.actor_id,
            output_format=request.output_format,
            database=scraper._db,
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
    except TimeoutError:
        logger.error(
            "replies search timeout conversation_id=%r timeout=%ss",
            request.conversation_id,
            timeout_seconds,
        )
        raise HTTPException(
            status_code=504, detail=f"Search timed out after {timeout_seconds} seconds"
        )
    except Exception as e:
        logger.exception(
            "replies search failed conversation_id=%r error=%s",
            request.conversation_id,
            e,
        )
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}") from e


@router.post(
    "/v1/search/profile/batch",
    tags=["Search"],
    operation_id="search_profile_batch",
    response_model=list[ProfileBatchResult],
)
async def search_profile_batch(
    request: ProfileBatchSearchRequest,
    scraper: TwitterScraper = Depends(get_scraper),
    timeout_seconds: int = Query(
        DEFAULT_TIMEOUT_SECONDS,
        ge=1,
        le=3600,
        description="Max time to wait for the batch to finish (seconds).",
    ),
) -> list[ProfileBatchResult]:
    """Search tweets from multiple user profiles in one request (looping per username)."""
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
        raise HTTPException(
            status_code=422,
            detail="usernames must contain at least one non-empty username",
        )

    temp_scraper = scraper_mod.TwitterScraper(
        apify_token=scraper.apify_token,
        actor_name=scraper.actor_id,
        output_format=request.output_format,
        database=scraper._db,
    )

    results: list[ProfileBatchResult] = []
    # Calculate timeout per username (distribute total timeout across all usernames)
    timeout_per_username = (
        max(1, timeout_seconds // len(usernames)) if usernames else timeout_seconds
    )

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
            results.append(
                ProfileBatchResult(username=username, items=items, error=None)
            )
        except TimeoutError:
            logger.error(
                "profile batch item timeout user=%r timeout=%ss",
                username,
                timeout_per_username,
            )
            if not request.continue_on_error:
                raise HTTPException(
                    status_code=504,
                    detail=f"Batch search timed out for username={username!r} after {timeout_per_username} seconds",
                )
            results.append(
                ProfileBatchResult(
                    username=username,
                    items=[],
                    error=f"Timeout after {timeout_per_username} seconds",
                )
            )
        except Exception as e:
            logger.exception("profile batch item failed user=%r error=%s", username, e)
            if not request.continue_on_error:
                raise HTTPException(
                    status_code=500,
                    detail=f"Batch search failed for username={username!r}: {str(e)}",
                ) from e
            results.append(
                ProfileBatchResult(username=username, items=[], error=str(e))
            )

    return results


@router.post(
    "/v1/search/profile/latest/batch",
    tags=["Search"],
    operation_id="search_profile_latest_batch",
    response_model=list[ProfileBatchResult],
)
async def search_profile_latest_batch(
    request: ProfileLatestBatchRequest,
    scraper: TwitterScraper = Depends(get_scraper),
    timeout_seconds: int = Query(
        DEFAULT_TIMEOUT_SECONDS,
        ge=1,
        le=3600,
        description="Max time to wait for the batch to finish (seconds).",
    ),
) -> list[ProfileBatchResult]:
    """Get the latest tweets from multiple user profiles in one request (looping per username)."""
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
        raise HTTPException(
            status_code=422,
            detail="usernames must contain at least one non-empty username",
        )

    temp_scraper = scraper_mod.TwitterScraper(
        apify_token=scraper.apify_token,
        actor_name=scraper.actor_id,
        output_format=request.output_format,
        database=scraper._db,
    )

    results: list[ProfileBatchResult] = []
    # Calculate timeout per username (distribute total timeout across all usernames)
    timeout_per_username = (
        max(1, timeout_seconds // len(usernames)) if usernames else timeout_seconds
    )

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
            results.append(
                ProfileBatchResult(username=username, items=items, error=None)
            )
        except TimeoutError:
            logger.error(
                "profile latest batch item timeout user=%r timeout=%ss",
                username,
                timeout_per_username,
            )
            if not request.continue_on_error:
                raise HTTPException(
                    status_code=504,
                    detail=f"Batch latest search timed out for username={username!r} after {timeout_per_username} seconds",
                )
            results.append(
                ProfileBatchResult(
                    username=username,
                    items=[],
                    error=f"Timeout after {timeout_per_username} seconds",
                )
            )
        except Exception as e:
            logger.exception(
                "profile latest batch item failed user=%r error=%s", username, e
            )
            if not request.continue_on_error:
                raise HTTPException(
                    status_code=500,
                    detail=f"Batch latest search failed for username={username!r}: {str(e)}",
                ) from e
            results.append(
                ProfileBatchResult(username=username, items=[], error=str(e))
            )

    return results



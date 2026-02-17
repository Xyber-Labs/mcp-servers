from fastapi import APIRouter, Depends, HTTPException, Query

from mcp_server_lurky.dependencies import get_db, get_lurky_client
from mcp_server_lurky.lurky.errors import (
    LurkyAPIError,
    LurkyAuthError,
    LurkyNotFoundError,
)
from mcp_server_lurky.lurky.module import LurkyClient
from mcp_server_lurky.schemas import SearchResponseSchema, SpaceDetailsSchema

router = APIRouter(tags=["Spaces"])


# --- Shared Business Logic Functions ---
# These functions contain the core logic and can be called by both REST and MCP endpoints


async def perform_search_spaces(
    q: str,
    limit: int,
    page: int,
    client: LurkyClient,
) -> SearchResponseSchema:
    """Core logic for searching spaces."""
    results = await client.search_discussions(q, limit=limit, page=page)
    # Convert from SearchResponse (lurky.models) to SearchResponseSchema (schemas)
    return SearchResponseSchema(**results.model_dump())


async def perform_get_space_details(
    space_id: str,
    client: LurkyClient,
    db,
) -> SpaceDetailsSchema:
    """Core logic for getting space details with caching."""
    # 1. Check cache (if database available)
    cached = None
    if db:
        cached = db.get_space(space_id)
    if cached:
        return SpaceDetailsSchema(
            id=cached.id,
            creator_id=cached.creator_id,
            creator_handle=cached.creator_handle,
            title=cached.title,
            summary=cached.summary,
            minimized_summary=cached.minimized_summary,
            state=cached.state,
            language=cached.language,
            overall_sentiment=cached.overall_sentiment,
            participant_count=cached.participant_count or 0,
            subscriber_count=cached.subscriber_count or 0,
            likes=cached.likes or 0,
            categories=cached.categories or [],
            created_at=int(cached.created_at.timestamp() * 1000)
            if cached.created_at
            else None,
            started_at=int(cached.started_at.timestamp() * 1000)
            if cached.started_at
            else None,
            scheduled_at=int(cached.scheduled_at.timestamp() * 1000)
            if cached.scheduled_at
            else None,
            ended_at=int(cached.ended_at.timestamp() * 1000)
            if cached.ended_at
            else None,
            analyzed_at=int(cached.analyzed_at.timestamp() * 1000)
            if cached.analyzed_at
            else None,
            discussions=[
                {
                    "id": d.id,
                    "space_id": d.space_id,
                    "title": d.title,
                    "summary": d.summary,
                    "timestamp": int(d.timestamp.timestamp() * 1000)
                    if d.timestamp
                    else None,
                    "coins": d.coins or [],
                    "categories": d.categories or [],
                }
                for d in cached.discussions
            ],
        )

    # 2. Fetch from API
    details = await client.get_space_details(space_id)
    # Fetch discussions
    discussions = await client.get_space_discussions(space_id)
    details.discussions = discussions

    # 3. Normalize to SpaceDetailsSchema for consistent response shape
    details_schema = SpaceDetailsSchema(**details.model_dump())

    # 4. Save to cache (if database available)
    if db:
        db.save_space(details_schema.model_dump())

    return details_schema


async def perform_get_latest_summaries(
    topic: str,
    count: int,
    client: LurkyClient,
    db,
) -> list[SpaceDetailsSchema]:
    """Core logic for getting latest summaries for a topic."""
    import logging

    logger = logging.getLogger(__name__)

    logger.info(f"Searching for latest {count} summaries for topic: '{topic}'")

    # Paginate through search results to find enough unique spaces
    # We need to account for duplicates (multiple discussions per space)
    # and potential failures when fetching details
    unique_space_ids = []
    page = 0
    max_pages = 10  # Limit pagination to prevent infinite loops
    discussions_seen = 0
    target_unique_spaces = count * 2  # Fetch 2x to account for failures

    while len(unique_space_ids) < target_unique_spaces and page < max_pages:
        search_limit = 20  # Max per page from API
        logger.debug(
            f"Searching page {page} with limit {search_limit} for topic '{topic}'"
        )

        search_results = await client.search_discussions(
            topic, limit=search_limit, page=page
        )
        discussions_seen += len(search_results.discussions)

        # Collect unique space IDs from this page
        page_unique_count = 0
        for d in search_results.discussions:
            if d.space_id and d.space_id not in unique_space_ids:
                unique_space_ids.append(d.space_id)
                page_unique_count += 1

        logger.debug(
            f"Page {page}: Found {len(search_results.discussions)} discussions, "
            f"{page_unique_count} new unique spaces (total unique: {len(unique_space_ids)})"
        )

        # If we got fewer results than requested, we've reached the end
        if len(search_results.discussions) < search_limit:
            logger.debug(f"Reached end of search results at page {page}")
            break

        # If no new unique spaces found on this page, stop paginating
        if page_unique_count == 0:
            logger.debug(
                f"No new unique spaces found on page {page}, stopping pagination"
            )
            break

        page += 1

    if not unique_space_ids:
        raise ValueError(
            f"No spaces found for topic: {topic} (searched {discussions_seen} discussions across {page + 1} pages)"
        )

    logger.info(
        f"Found {len(unique_space_ids)} unique spaces from {discussions_seen} discussions "
        f"(searched {page + 1} pages), requesting {count} summaries"
    )

    # Fetch details for each space ID until we have the requested count
    summaries = []
    failed_count = 0

    for idx, sid in enumerate(unique_space_ids, 1):
        if len(summaries) >= count:
            logger.debug(f"Reached requested count of {count} summaries, stopping")
            break

        logger.debug(f"Fetching space {idx}/{len(unique_space_ids)}: {sid}")

        try:
            # Use the cache-aware helper (it will log cache hits/misses internally)
            details = await perform_get_space_details(sid, client, db)
            summaries.append(details)
            logger.debug(
                f"Successfully fetched summary {len(summaries)}/{count} for space {sid}"
            )
        except Exception as e:
            failed_count += 1
            logger.warning(f"Failed to fetch details for space {sid}: {e}")
            continue

    logger.info(
        f"Summary fetch complete: {len(summaries)}/{count} summaries retrieved, "
        f"{failed_count} failures (cache hits/misses logged by database manager)"
    )

    if not summaries:
        raise ValueError(
            f"No summaries found for topic: {topic} "
            f"(attempted {len(unique_space_ids)} spaces, {failed_count} failed)"
        )

    if len(summaries) < count:
        logger.warning(
            f"Requested {count} summaries but only found {len(summaries)}. "
            f"Searched {discussions_seen} discussions across {page + 1} pages, "
            f"found {len(unique_space_ids)} unique spaces, {failed_count} failed to fetch"
        )

    return summaries


# --- FastAPI Route Handlers ---
# These are the REST endpoints that use the shared business logic functions


@router.get(
    "/search",
    response_model=SearchResponseSchema,
    operation_id="lurky_search_spaces",
    summary="Search Twitter Spaces",
    description="""
Search for Twitter Spaces discussions based on a keyword or phrase.

Returns a list of discussions that match the search term, including space metadata
and summary information. Results are paginated.

**Examples:**
- Search for crypto discussions: `q=bitcoin`
- Search for AI topics: `q=artificial intelligence`
- Search for specific projects: `q=ethereum defi`
""",
)
async def search_spaces(
    q: str = Query(
        ...,
        description="Search keyword or phrase (e.g., 'bitcoin', 'AI agents', 'crypto news')",
        examples=["bitcoin", "artificial intelligence", "defi"],
    ),
    limit: int = Query(
        10, ge=1, le=20, description="Number of results per page (1-20)"
    ),
    page: int = Query(0, ge=0, description="Page number for pagination (0-indexed)"),
    client: LurkyClient = Depends(get_lurky_client),
):
    """Search for discussions based on a keyword."""
    try:
        return await perform_search_spaces(q, limit, page, client)
    except LurkyAuthError as e:
        raise HTTPException(status_code=401, detail="Invalid API key") from e
    except LurkyAPIError as e:
        raise HTTPException(status_code=e.status_code or 502, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get(
    "/spaces/{space_id}",
    response_model=SpaceDetailsSchema,
    operation_id="lurky_get_space_details",
    summary="Get Space Details",
    description="""
Get full details, summary, and segmented discussions for a specific Twitter Space.

The `space_id` can be obtained from search results or directly from Twitter Space URLs.
Results are cached locally to minimize API calls.

**Response includes:**
- Space metadata (title, creator, timestamps)
- AI-generated summary and minimized summary
- Sentiment analysis
- Segmented discussions with individual summaries
""",
)
async def get_space_details(
    space_id: str, client: LurkyClient = Depends(get_lurky_client), db=Depends(get_db)
):
    """Get full details and summary for a specific Space ID."""
    try:
        return await perform_get_space_details(space_id, client, db)
    except LurkyNotFoundError as e:
        raise HTTPException(
            status_code=404, detail=f"Space {space_id} not found"
        ) from e
    except LurkyAuthError as e:
        raise HTTPException(status_code=401, detail="Invalid API key") from e
    except LurkyAPIError as e:
        raise HTTPException(status_code=e.status_code or 502, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get(
    "/latest-summaries",
    response_model=list[SpaceDetailsSchema],
    operation_id="lurky_get_latest_summaries",
    summary="Get Latest Summaries by Topic",
    description="""
Fetch the latest unique Twitter Space summaries for a given topic.

The `topic` parameter is a **search keyword** (same as the `/search` endpoint).
This endpoint searches for spaces matching the topic, then fetches full details
for each unique space found.

**How it works:**
1. Searches for discussions matching the topic keyword
2. Extracts unique Space IDs from results
3. Fetches full details for each space (with caching)
4. Returns up to `count` unique space summaries

**Example topics:**
- `bitcoin` - Get latest Bitcoin-related Space summaries
- `AI agents` - Get latest AI agent discussions
- `solana defi` - Get latest Solana DeFi discussions
""",
)
async def get_latest_summaries(
    topic: str = Query(
        ...,
        description="Search keyword to find spaces (e.g., 'bitcoin', 'ethereum', 'AI agents')",
        examples=["bitcoin", "AI agents", "crypto news", "solana defi"],
    ),
    count: int = Query(
        3,
        ge=1,
        le=10,
        description="Number of unique space summaries to return (1-10)",
    ),
    client: LurkyClient = Depends(get_lurky_client),
    db=Depends(get_db),
):
    """Fetch the latest N unique space summaries for a given topic."""
    try:
        return await perform_get_latest_summaries(topic, count, client, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except LurkyAuthError as e:
        raise HTTPException(status_code=401, detail="Invalid API key") from e
    except LurkyAPIError as e:
        raise HTTPException(status_code=e.status_code or 502, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

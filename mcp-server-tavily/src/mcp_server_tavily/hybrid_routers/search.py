import logging

from fastapi import APIRouter, Depends, Header, HTTPException

from mcp_server_tavily.dependencies import get_tavily_client
from mcp_server_tavily.schemas import SearchRequest, TavilySearchResultResponse
from mcp_server_tavily.tavily import (
    TavilyApiError,
    TavilyConfigError,
    TavilyEmptyQueryError,
    TavilyEmptyResultsError,
    TavilyInvalidResponseError,
    TavilyServiceError,
    _TavilyService,
)

logger = logging.getLogger(__name__)
router = APIRouter()
API_KEY_HEADER = "Tavily-Api-Key"


@router.post(
    "/search",
    tags=["Search"],
    operation_id="tavily_search",
    response_model=list[TavilySearchResultResponse],
)
async def tavily_search(
    search: SearchRequest,
    tavily_api_key: str | None = Header(
        default=None,
        alias=API_KEY_HEADER,
        description=(
            "Tavily API key used to authorize this search request. "
            "Optional: if not provided, the server will use TAVILY_API_KEY from environment. "
            "If provided, this header takes precedence over the environment variable."
        ),
    ),
    tavily_client: _TavilyService = Depends(get_tavily_client),
) -> list[TavilySearchResultResponse]:
    try:
        results = await tavily_client.search(
            query=search.query,
            max_results=search.max_results,
            api_key=tavily_api_key,
            search_depth=search.search_depth,
        )
        formatted_results = [
            TavilySearchResultResponse(
                title=result.title,
                url=result.url,
                content=result.content,
            )
            for result in results
        ]
        logger.info(f"Successfully retrieved {len(formatted_results)} search results")
        return formatted_results
    except TavilyEmptyQueryError as e:
        logger.warning(f"Empty query error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except TavilyConfigError as e:
        logger.error(f"Configuration error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except TavilyEmptyResultsError as e:
        logger.info(f"No results found: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except (TavilyApiError, TavilyInvalidResponseError) as e:
        logger.error(f"Tavily API error: {e}")
        raise HTTPException(status_code=503, detail=str(e))
    except TavilyServiceError as e:
        logger.error(f"Tavily service error: {e}")
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in tavily_search: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")


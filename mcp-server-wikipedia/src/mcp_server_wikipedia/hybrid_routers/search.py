import logging

from fastapi import APIRouter, Depends
from pydantic import ValidationError as PydanticValidationError

from mcp_server_wikipedia.dependencies import get_wiki_service
from mcp_server_wikipedia.schemas import SearchWikipediaRequest, SearchWikipediaResponse
from mcp_server_wikipedia.wikipedia import WikipediaAPIError, _WikipediaService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/search",
    tags=["Wikipedia"],
    operation_id="search_wikipedia",
    response_model=SearchWikipediaResponse,
)
async def search_wikipedia(
    params: SearchWikipediaRequest,
    wiki_service: _WikipediaService = Depends(get_wiki_service),
) -> SearchWikipediaResponse:
    """
    Search Wikipedia for articles matching a query and return a list of titles.

    This tool allows AI agents to discover Wikipedia articles relevant to a search query.
    """
    try:
        results = await wiki_service.search(params.query, limit=params.limit)
        return SearchWikipediaResponse(results=results)
    except PydanticValidationError as ve:
        error_details = "\n".join(
            f"  - {'.'.join(str(loc).capitalize() for loc in err['loc'])}: {err['msg']}"
            for err in ve.errors()
        )
        raise ValueError(f"Invalid parameters:\n{error_details}") from ve
    except ValueError as e:
        raise ValueError(f"Input validation error: {e}") from e
    except WikipediaAPIError as e:
        raise RuntimeError(f"Wikipedia API error: {e}") from e

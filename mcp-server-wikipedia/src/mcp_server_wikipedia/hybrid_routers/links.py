import logging
from typing import List

from fastapi import APIRouter, Request
from pydantic import ValidationError as PydanticValidationError

from mcp_server_wikipedia.schemas import GetLinksRequest
from mcp_server_wikipedia.wikipedia import (
    ArticleNotFoundError,
    WikipediaAPIError,
    _WikipediaService,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/links",
    tags=["Wikipedia"],
    operation_id="get_wikipedia_links",
)
async def get_links(request: Request, params: GetLinksRequest) -> List[str]:
    """
    Get the links contained within a Wikipedia article.

    This tool allows AI agents to discover related articles and explore
    connections between Wikipedia topics.
    """
    try:
        wiki_service: _WikipediaService = request.app.state.wiki_service
        links = await wiki_service.get_links(params.title)
        return links
    except PydanticValidationError as ve:
        error_details = "\n".join(
            f"  - {'.'.join(str(loc).capitalize() for loc in err['loc'])}: {err['msg']}"
            for err in ve.errors()
        )
        raise ValueError(f"Invalid parameters:\n{error_details}") from ve
    except ArticleNotFoundError as e:
        raise ValueError(str(e)) from e
    except WikipediaAPIError as e:
        raise RuntimeError(f"Wikipedia API error: {e}") from e

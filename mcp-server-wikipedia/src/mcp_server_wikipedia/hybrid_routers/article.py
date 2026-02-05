import logging
from typing import Any, Dict

from fastapi import APIRouter, Request
from pydantic import ValidationError as PydanticValidationError

from mcp_server_wikipedia.schemas import GetArticleRequest
from mcp_server_wikipedia.wikipedia import (
    ArticleNotFoundError,
    WikipediaAPIError,
    _WikipediaService,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/article",
    tags=["Wikipedia"],
    operation_id="get_wikipedia_article",
)
async def get_article(request: Request, params: GetArticleRequest) -> Dict[str, Any]:
    """
    Get the full content and metadata of a Wikipedia article by its exact title.

    This tool provides comprehensive information about a Wikipedia article including
    its full text, summary, sections, links, and URL.
    """
    try:
        wiki_service: _WikipediaService = request.app.state.wiki_service
        article = await wiki_service.get_article(params.title)
        return article
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

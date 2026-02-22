import logging

from fastapi import APIRouter, Depends
from pydantic import ValidationError as PydanticValidationError

from mcp_server_wikipedia.dependencies import get_wiki_service
from mcp_server_wikipedia.schemas import ArticleResponse, GetArticleRequest
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
    operation_id="get_article",
    response_model=ArticleResponse,
)
async def get_article(
    params: GetArticleRequest,
    wiki_service: _WikipediaService = Depends(get_wiki_service),
) -> ArticleResponse:
    """
    Get the full content and metadata of a Wikipedia article by its exact title.

    This tool provides comprehensive information about a Wikipedia article including
    its full text, summary, sections, links, and URL.
    """
    try:
        article = await wiki_service.get_article(params.title)
        return ArticleResponse(**article)
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

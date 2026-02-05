import logging

from fastapi import APIRouter, Request
from pydantic import ValidationError as PydanticValidationError

from mcp_server_wikipedia.schemas import GetSummaryRequest
from mcp_server_wikipedia.wikipedia import (
    ArticleNotFoundError,
    WikipediaAPIError,
    _WikipediaService,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/summary",
    tags=["Wikipedia"],
    operation_id="get_wikipedia_summary",
)
async def get_summary(request: Request, params: GetSummaryRequest) -> str:
    """
    Get a summary of a Wikipedia article.

    This tool provides a concise overview of an article, useful for quick
    understanding without retrieving the full content.
    """
    try:
        wiki_service: _WikipediaService = request.app.state.wiki_service
        summary = await wiki_service.get_summary(params.title)
        return summary
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

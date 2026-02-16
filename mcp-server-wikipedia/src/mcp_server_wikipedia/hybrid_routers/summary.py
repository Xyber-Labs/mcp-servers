import logging

from fastapi import APIRouter, Depends
from pydantic import ValidationError as PydanticValidationError

from mcp_server_wikipedia.dependencies import get_wiki_service
from mcp_server_wikipedia.schemas import GetSummaryRequest, SummaryResponse
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
    operation_id="get_summary",
    response_model=SummaryResponse,
)
async def get_summary(
    params: GetSummaryRequest,
    wiki_service: _WikipediaService = Depends(get_wiki_service),
) -> SummaryResponse:
    """
    Get a summary of a Wikipedia article.

    This tool provides a concise overview of an article, useful for quick
    understanding without retrieving the full content.
    """
    try:
        summary = await wiki_service.get_summary(params.title)
        return SummaryResponse(title=params.title, summary=summary)
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

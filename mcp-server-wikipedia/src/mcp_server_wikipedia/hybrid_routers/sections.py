import logging

from fastapi import APIRouter, Depends
from pydantic import ValidationError as PydanticValidationError

from mcp_server_wikipedia.dependencies import get_wiki_service
from mcp_server_wikipedia.schemas import GetSectionsRequest, SectionsResponse
from mcp_server_wikipedia.wikipedia import (
    ArticleNotFoundError,
    WikipediaAPIError,
    _WikipediaService,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/sections",
    tags=["Wikipedia"],
    operation_id="get_sections",
    response_model=SectionsResponse,
)
async def get_sections(
    params: GetSectionsRequest,
    wiki_service: _WikipediaService = Depends(get_wiki_service),
) -> SectionsResponse:
    """
    Get the section titles of a Wikipedia article.

    This tool helps AI agents understand the structure of an article and
    navigate to specific topics within it.
    """
    try:
        sections = await wiki_service.get_sections(params.title)
        return SectionsResponse(title=params.title, sections=sections)
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

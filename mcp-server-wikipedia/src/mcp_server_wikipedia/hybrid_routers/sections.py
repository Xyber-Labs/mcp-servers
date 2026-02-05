import logging
from typing import List

from fastapi import APIRouter, Request
from pydantic import ValidationError as PydanticValidationError

from mcp_server_wikipedia.schemas import GetSectionsRequest
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
    operation_id="get_wikipedia_sections",
)
async def get_sections(request: Request, params: GetSectionsRequest) -> List[str]:
    """
    Get the section titles of a Wikipedia article.

    This tool helps AI agents understand the structure of an article and
    navigate to specific topics within it.
    """
    try:
        wiki_service: _WikipediaService = request.app.state.wiki_service
        sections = await wiki_service.get_sections(params.title)
        return sections
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

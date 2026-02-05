import logging
from typing import List

from fastapi import APIRouter, Request
from pydantic import ValidationError as PydanticValidationError

from mcp_server_wikipedia.schemas import GetRelatedTopicsRequest
from mcp_server_wikipedia.wikipedia import (
    ArticleNotFoundError,
    WikipediaAPIError,
    _WikipediaService,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/related-topics",
    tags=["Wikipedia"],
    operation_id="get_wikipedia_related_topics",
)
async def get_related_topics(request: Request, params: GetRelatedTopicsRequest) -> List[str]:
    """
    Get topics related to a Wikipedia article based on its internal links.

    This tool helps AI agents discover related topics and explore connections
    within Wikipedia's knowledge graph.
    """
    try:
        wiki_service: _WikipediaService = request.app.state.wiki_service
        topics = await wiki_service.get_related_topics(params.title, params.limit)
        return topics
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

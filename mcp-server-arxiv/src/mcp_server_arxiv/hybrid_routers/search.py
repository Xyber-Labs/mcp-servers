import logging

from fastapi import APIRouter, Depends, HTTPException

from mcp_server_arxiv.dependencies import get_arxiv_client
from mcp_server_arxiv.schemas import ArxivPaperResponse, SearchRequest
from mcp_server_arxiv.xy_arxiv import (
    ArxivApiError,
    ArxivServiceError,
    _ArxivService,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/search",
    tags=["Search"],
    operation_id="arxiv_search",
    response_model=list[ArxivPaperResponse],
)
async def arxiv_search(
    search: SearchRequest,
    arxiv_client: _ArxivService = Depends(get_arxiv_client),
) -> list[ArxivPaperResponse]:
    """
    Search ArXiv papers by query or fetch a specific paper by ID.
    
    This endpoint supports two modes:
    1. Query-based search: Provide 'query' to search for papers
    2. ID-based lookup: Provide 'arxiv_id' to fetch a specific paper
    
    Both modes return metadata and optionally full PDF text content.
    """
    try:
        results = await arxiv_client.search(
            query=search.query,
            arxiv_id=search.arxiv_id,
            max_results=search.max_results,
            max_text_length=search.max_text_length,
        )

        paper_responses = [
            ArxivPaperResponse.from_search_result(result) for result in results
        ]
        logger.info(f"Successfully retrieved {len(paper_responses)} paper results")
        return paper_responses

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=422, detail=str(e))
    except ArxivApiError as e:
        logger.error(f"ArXiv API error: {e}")
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=503, detail=str(e))
    except ArxivServiceError as e:
        logger.error(f"ArXiv service error: {e}")
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in arxiv_search: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")


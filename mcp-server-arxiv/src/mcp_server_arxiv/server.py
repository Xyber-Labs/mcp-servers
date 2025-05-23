from collections.abc import AsyncIterator
import logging
from contextlib import asynccontextmanager
from typing import Any, Literal
from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError

from mcp_server_arxiv.arxiv import (
    _ArxivService,
    get_arxiv_service,
    ArxivServiceError,
    ArxivConfigError,
    ArxivApiError,
    ArxivSearchResult,
)

logger = logging.getLogger(__name__)

# --- Lifespan Management --- #
@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[dict[str, Any]]:
    """Manage server startup/shutdown. Initializes the ArXiv service."""
    logger.info("Lifespan: Initializing services...")
    
    try:
        # Initialize services
        arxiv_service: _ArxivService = get_arxiv_service()
        
        logger.info("Lifespan: Services initialized successfully")
        yield {"arxiv_service": arxiv_service}
    
    except (ArxivConfigError, ArxivServiceError) as init_err:
        logger.error(f"FATAL: Lifespan initialization failed: {init_err}", exc_info=True)
        raise init_err
    
    except Exception as startup_err:
        logger.error(f"FATAL: Unexpected error during lifespan initialization: {startup_err}", exc_info=True)
        raise startup_err
    
    finally:
        logger.info("Lifespan: Shutdown cleanup completed")

# --- MCP Server Initialization --- #
mcp_server = FastMCP(
    name="arxiv",
    description="Search arXiv for scientific papers and extract their content",
    lifespan=app_lifespan
)

# --- Tool Definitions --- #
@mcp_server.tool()
async def arxiv_search(
    ctx: Context,
    query: str,  # The search query string for ArXiv
    max_results: int | None = None,  # Optional override for the maximum number of results to fetch and process (1-50)
    max_text_length: int | None = None,  # Optional max characters of full text per paper (min 100)
) -> str:
    """Searches arXiv for scientific papers based on a query, downloads PDFs, extracts text, and returns formatted results."""
    arxiv_service = ctx.request_context.lifespan_context["arxiv_service"]

    try:
        # Execute core logic
        search_results: list[ArxivSearchResult] = await arxiv_service.search(
            query=query,
            max_results_override=max_results,
            max_text_length_override=max_text_length
        )
        
        # Format response
        if not search_results:
            logger.info("No relevant papers found or processed on arXiv for the given query")
            return "No relevant papers found or processed on arXiv for the given query"
        
        formatted_items = ["ArXiv Search Results:\n"]
        for i, result in enumerate(search_results):
            formatted_items.append(f"\n--- Paper {i+1} ---\n{str(result)}")
        
        formatted_response = "\n".join(formatted_items)
        logger.info(f"Successfully processed search request. Returning {len(search_results)} formatted ArXiv results")
        
        return formatted_response
    
    except ValueError as val_err:
        logger.warning(f"Input validation error: {val_err}")
        raise ToolError(f"Input validation error: {val_err}") from val_err
    
    except ArxivApiError as api_err:
        logger.error(f"ArXiv API error: {api_err}", exc_info=True)
        raise ToolError(f"ArXiv API error: {api_err}") from api_err
    
    except ArxivServiceError as service_err:
        logger.error(f"ArXiv service error: {service_err}", exc_info=True)
        raise ToolError(f"ArXiv service error: {service_err}") from service_err
    
    except Exception as e:
        logger.error(f"Unexpected error during search: {e}", exc_info=True)
        raise ToolError("An unexpected error occurred during search.") from e
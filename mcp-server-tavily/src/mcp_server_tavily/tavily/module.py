import logging
from functools import lru_cache
from typing import Any
from langchain_tavily import TavilySearch

from mcp_server_tavily.tavily.config import TavilyConfig
from mcp_server_tavily.tavily.errors import (
    TavilyApiError,
    TavilyConfigError,
    TavilyEmptyQueryError,
    TavilyEmptyResultsError,
    TavilyInvalidResponseError,
    TavilyServiceError,
)
from mcp_server_tavily.tavily.models import TavilyApiResponse, TavilySearchResult
from tenacity import (
    RetryCallState,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)


def final_failure_callback(retry_state:RetryCallState):
    exception: BaseException | None = None
    result = None
    if retry_state.outcome:
        exception = retry_state.outcome.exception()
        if not exception:
            result = retry_state.outcome.result()
    logger.error(f"Failed to retry after #{retry_state.attempt_number} attempts.  Cause: {str(type(exception).__name__) + '<-' + str(exception) if exception else ("function returned "+str(result))}.")
    if exception:
        raise exception

def retry_callback(retry_state:RetryCallState):
    exception: BaseException | None  = None
    result = None
    if retry_state.outcome:
        exception= retry_state.outcome.exception()
        if not exception:
            result = retry_state.outcome.result()
    logger.warning(f"Retry #{retry_state.attempt_number}. Cause: {str(type(exception).__name__) + '<-' + str(exception) if exception else ("function returned "+str(result))}. Time until next retry: {retry_state.upcoming_sleep}.")

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(min=0.5),
    retry=retry_if_exception_type(TavilyApiError),
    retry_error_callback=final_failure_callback,
    before_sleep=retry_callback,
)
async def _ainvoke_with_retry(tool: TavilySearch, query: str) -> dict[str, Any]:
    try:
        return await tool.ainvoke(query)
    except Exception as e:
        raise TavilyApiError(f"Search failed<-{type(e).__name__}<-{e}") from e

class _TavilyService:
    """Encapsulates Tavily client logic and configuration."""

    def __init__(self, config: TavilyConfig):
        self.config = config
        logger.info("TavilyService initialized.")

    def _resolve_api_key(self, api_key: str | None) -> str:
        """
        Resolve the effective API key, prioritizing the header-provided key.
        """
        key = api_key or self.config.api_key
        if not key:
            raise TavilyServiceError(
                "Tavily API key is not configured and was not provided in the header."
            )
        return key

    def _create_tavily_tool(
        self,
        max_results: int | None = None,
        api_key: str | None = None,
        search_depth: str | None = None,
    ) -> Any:
        """Creates an instance of the TavilySearch tool with current config."""
        try:
            resolved_key = self._resolve_api_key(api_key)
            return TavilySearch(
                tavily_api_key=resolved_key,
                max_results=max_results or self.config.max_results,
                topic=self.config.topic,
                search_depth=search_depth or self.config.search_depth,
                include_answer=self.config.include_answer,
                include_raw_content=self.config.include_raw_content,
                include_images=self.config.include_images,
            )
        except Exception as e:
            logger.error(
                f"Passed TavilyConfig did not match TavilySearch parameters schema: {self.config}",
                exc_info=True,
            )
            raise TavilyConfigError(f"Error creating TavilySearch tool: {e}") from e

    async def search(
        self,
        query: str,
        max_results: int | None = None,
        api_key: str | None = None,
        search_depth: str | None = None,
    ) -> list[TavilySearchResult]:
        """
        Performs a web search using the Tavily API.

        Args:
            query: The search query string.
            max_results: Optional override for the maximum number of results.
            api_key: Optional API key override.
            search_depth: Optional search depth override ('basic' or 'advanced').

        Returns:
            A list of TavilySearchResult objects on success.

        Raises:
            TavilyEmptyQueryError: If query is empty.
            TavilyConfigError: If tool creation fails.
            TavilyServiceError: For general client issues.
            TavilyApiError: For errors during the Tavily API call.
            TavilyEmptyResultsError: If API returns empty results.
            TavilyInvalidResponseError: If API returns invalid response format.

        """
        if not query:
            logger.warning("Received empty query for Tavily search.")
            raise TavilyEmptyQueryError("Search query cannot be empty.")

        logger.debug(f"Performing Tavily search for query: '{query[:100]}...'")
        tool = self._create_tavily_tool(
            max_results=max_results, api_key=api_key, search_depth=search_depth
        )

        # Perform search
        raw_results = await _ainvoke_with_retry(tool, query)

        logger.debug(f"Tavily raw response type: {type(raw_results)}")
        logger.debug(f"Tavily raw response: {raw_results}")

        # Validate and parse response using Pydantic model
        try:
            api_response = TavilyApiResponse.from_raw_response(raw_results)
        except (
            TavilyApiError,
            TavilyInvalidResponseError,
            TavilyEmptyResultsError,
        ):
            # Re-raise known errors
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error parsing Tavily response: {e}", exc_info=True
            )
            raise TavilyInvalidResponseError(
                f"Failed to parse Tavily API response: {e}"
            ) from e

        # Convert to TavilySearchResult list
        search_results = api_response.to_search_results()

        if not search_results:
            logger.warning("Tavily response could not be converted to search results.")
            raise TavilyEmptyResultsError("No results were found for this search query.")

        logger.info(
            f"Tavily search successful, processed {len(search_results)} results."
        )
        return search_results


@lru_cache(maxsize=1)
def get_tavily_service() -> _TavilyService:
    """
    Factory function to get a singleton instance of the Tavily service.
    Handles configuration loading and service initialization.

    Returns:
        An initialized _TavilyService instance.

    Raises:
        TavilyConfigError: If configuration loading or validation fails.
        TavilyServiceError: If the langchain-tavily package isn't installed.

    """
    config = TavilyConfig()
    service = _TavilyService(config=config)
    logger.info("Tavily service instance retrieved successfully.")
    return service

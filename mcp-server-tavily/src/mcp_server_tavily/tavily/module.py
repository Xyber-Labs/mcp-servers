import logging
from typing import Any
from functools import lru_cache
import json
from langchain_tavily import TavilySearch
from langchain_core.documents import Document
from mcp_server_tavily.tavily.config import TavilyConfig, TavilyServiceError, TavilyApiError, TavilyConfigError
from mcp_server_tavily.tavily.models import TavilySearchResult

logger = logging.getLogger(__name__)

class _TavilyService:
    """Encapsulates Tavily client logic and configuration."""

    def __init__(self, config: TavilyConfig):
        self.config = config
        logger.info("TavilyService initialized.")

    def _create_tavily_tool(self, max_results: int | None = None) -> Any:
        """Creates an instance of the TavilySearch tool with current config."""
        
        try:
            return TavilySearch(
                api_key=self.config.api_key,
                max_results = max_results or self.config.max_results,
                topic=self.config.topic,
                search_depth=self.config.search_depth,
                include_answer=self.config.include_answer,
                include_raw_content=self.config.include_raw_content,
                include_images=self.config.include_images
            )
        except Exception as e:
            logger.error(f"Passed TavilyConfig did not match TavilySearch parameters schema: {self.config}", exc_info=True)
            raise TavilyConfigError(f"Error creating TavilySearch tool: {e}") from e

    async def search(self, query: str, max_results: int | None = None) -> list[TavilySearchResult]:
        """
        Performs a web search using the Tavily API.

        Args:
            query: The search query string.
            max_results: Optional override for the maximum number of results.

        Returns:
            A list of search result dictionaries on success.

        Raises:
            TavilyApiError: For errors during the Tavily API call.
            TavilyServiceError: For general client issues.
        """
        
        if not query:
            logger.warning("Received empty query for Tavily search.")
            raise ValueError("Search query cannot be empty.")
        
        logger.info(f"Performing Tavily search for query: '{query[:100]}...'")

        try:
            # Create tool
            tool = self._create_tavily_tool(max_results=max_results)

            # Perform search
            results = await tool.ainvoke(query)
            
            logger.debug(f"Tavily raw response type: {type(results)}")
            logger.debug(f"Tavily raw response: {results}")
            
            if not results:
                logger.warning("Tavily returned empty results.")
                return [TavilySearchResult(title="No Results", url="#", content="No results were found for this search query.")]
            
            if results == "error":
                logger.warning("Tavily returned an error.")
                return [TavilySearchResult(title="Search Error", url="#", content="The Tavily API returned an error. This might be due to API key issues, rate limiting, or service unavailability.")]
            
            if isinstance(results, str):
                logger.warning(f"Tavily returned a string instead of a list: {results}")
                return [TavilySearchResult(title="Search Result", url="#", content=results)]
            
            # Handle dictionary response from Tavily API
            if isinstance(results, dict):
                # Extract the actual search results from the 'results' key
                search_results = results.get('results', [])
                if not search_results:
                    # If no results key, try to use the answer if available
                    answer = results.get('answer', '')
                    if answer:
                        return [TavilySearchResult(title="Search Answer", url="#", content=answer)]
                    else:
                        return [TavilySearchResult(title="No Results", url="#", content="No search results found.")]
                
                # Process the actual search results
                processed_results = []
                for i, result in enumerate(search_results):
                    if isinstance(result, dict):
                        title = result.get('title', f"Search Result {i+1}")
                        url = result.get('url', '#')
                        content = result.get('content', result.get('snippet', ''))
                        processed_results.append(TavilySearchResult(title=title, url=url, content=content))
                    else:
                        processed_results.append(TavilySearchResult(
                            title=f"Search Result {i+1}",
                            url="#",
                            content=str(result)
                        ))
                
                logger.info(f"Tavily search successful, processed {len(processed_results)} results.")
                return processed_results
            
            # Handle list response (fallback for other formats)
            if isinstance(results, list):
                processed_results = []
                for i, result in enumerate(results):
                    if isinstance(result, str):
                        # If result is a string, create a TavilySearchResult with the string as content
                        processed_results.append(TavilySearchResult(
                            title=f"Search Result {i+1}", 
                            url="#", 
                            content=result
                        ))
                    elif hasattr(result, 'title') and hasattr(result, 'url') and hasattr(result, 'content'):
                        # If result has the expected attributes, use them
                        processed_results.append(TavilySearchResult(
                            title=result.title, 
                            url=result.url, 
                            content=result.content
                        ))
                    elif hasattr(result, 'page_content') and hasattr(result, 'metadata'):
                        # Handle Document objects from langchain
                        metadata = result.metadata or {}
                        processed_results.append(TavilySearchResult(
                            title=metadata.get('title', f"Search Result {i+1}"),
                            url=metadata.get('source', '#'),
                            content=result.page_content
                        ))
                    else:
                        # Fallback for unknown result types
                        processed_results.append(TavilySearchResult(
                            title=f"Search Result {i+1}",
                            url="#",
                            content=str(result)
                        ))
                
                logger.info(f"Tavily search successful, processed {len(processed_results)} results.")
                return processed_results
            
            # Fallback for unexpected response types
            logger.warning(f"Unexpected Tavily response type: {type(results)}")
            return [TavilySearchResult(title="Search Result", url="#", content=str(results))]

        except Exception as e:
            logger.error(f"Error during Tavily API call for query '{query}': {e}", exc_info=True)
            return [TavilySearchResult(title="Search Error", url="#", content=f"An error occurred during the search: {str(e)}")]

 
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
    
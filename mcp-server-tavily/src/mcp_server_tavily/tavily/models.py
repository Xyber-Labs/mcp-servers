from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field, model_validator


@dataclass(frozen=True)
class TavilySearchResult:
    """Represents a search result from the Tavily API."""

    title: str
    url: str
    content: str

    def __str__(self) -> str:
        """Returns a string representation of the TavilySearchResult object."""
        return f"Title: {self.title}\nURL: {self.url}\nContent: {self.content}"


class TavilyResultItem(BaseModel):
    """Represents a single result item from Tavily API."""

    title: str = Field(default="")
    url: str = Field(default="#")
    content: str = Field(default="")
    snippet: str | None = Field(default=None)

    @model_validator(mode="after")
    def ensure_content(self) -> TavilyResultItem:
        """Ensure content is populated from snippet if content is empty."""
        if not self.content and self.snippet:
            # Create a new instance with content set from snippet
            return TavilyResultItem(
                title=self.title,
                url=self.url,
                content=self.snippet,
                snippet=None,
            )
        return self


class TavilyApiResponse(BaseModel):
    """Pydantic model for Tavily API response structure."""

    results: list[TavilyResultItem] | None = Field(default=None)
    answer: str | None = Field(default=None)

    @model_validator(mode="after")
    def validate_not_empty(self) -> TavilyApiResponse:
        """Validate that the response contains either results or an answer."""
        if not self.results and not self.answer:
            from mcp_server_tavily.tavily.errors import TavilyEmptyResultsError
            raise TavilyEmptyResultsError("No results were found for this search query.")
        return self

    @classmethod
    def from_raw_response(cls, data: Any) -> TavilyApiResponse:
        """
        Create TavilyApiResponse from raw API response.
        
        Handles various response formats:
        - Dict with 'results' key
        - Dict with 'answer' key
        - List of result items
        - String (error case - will raise exception)
        """
        if isinstance(data, str):
            if data == "error":
                from mcp_server_tavily.tavily.errors import TavilyApiError
                raise TavilyApiError("Tavily API returned an error response")
            # If it's a non-error string, treat as answer
            return cls(answer=data, results=None)

        if isinstance(data, dict):
            results = data.get("results")
            answer = data.get("answer")
            
            processed_results = None
            if results:
                if isinstance(results, list):
                    processed_results = []
                    for item in results:
                        if isinstance(item, dict):
                            # Handle both 'content' and 'snippet' fields
                            item_dict = dict(item)
                            if "content" not in item_dict and "snippet" in item_dict:
                                item_dict["content"] = item_dict.get("snippet", "")
                            processed_results.append(TavilyResultItem(**item_dict))
                        else:
                            processed_results.append(
                                TavilyResultItem(title=str(item), content=str(item))
                            )
            
            return cls(results=processed_results, answer=answer)

        if isinstance(data, list):
            processed_results = [
                TavilyResultItem(**item) if isinstance(item, dict)
                else TavilyResultItem(title=str(item), content=str(item))
                for item in data
            ]
            return cls(results=processed_results, answer=None)

        # Fallback for unexpected types
        from mcp_server_tavily.tavily.errors import TavilyInvalidResponseError
        raise TavilyInvalidResponseError(
            f"Unexpected Tavily response type: {type(data)}"
        )

    def to_search_results(self) -> list[TavilySearchResult]:
        """Convert TavilyApiResponse to list of TavilySearchResult."""
        results = []
        
        # If we have an answer but no results, create a result from the answer
        if self.answer and not self.results:
            results.append(
                TavilySearchResult(
                    title="Search Answer",
                    url="#",
                    content=self.answer,
                )
            )
        elif self.results:
            for item in self.results:
                results.append(
                    TavilySearchResult(
                        title=item.title or "Search Result",
                        url=item.url or "#",
                        content=item.content or "",
                    )
                )
        
        return results

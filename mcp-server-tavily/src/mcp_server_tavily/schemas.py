from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=1,
        max_length=512,
        description="The search query string for Tavily",
    )
    max_results: int | None = Field(
        None,
        ge=1,
        le=50,
        description="Optional override for the maximum number of search results (min 1, max 50)",
    )
    search_depth: str = Field(
        default="basic",
        pattern="^(basic|advanced)$",
        description="Search depth level: 'basic' or 'advanced'",
    )


class TavilySearchResultResponse(BaseModel):
    """Response model for a single Tavily search result."""

    title: str = Field(description="Title of the search result")
    url: str = Field(description="URL of the search result")
    content: str = Field(description="Content/snippet from the search result")

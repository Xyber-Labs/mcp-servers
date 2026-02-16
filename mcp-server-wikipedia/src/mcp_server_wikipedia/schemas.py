from typing import Any

from pydantic import BaseModel, Field


class SearchWikipediaRequest(BaseModel):
    """Input schema for searching Wikipedia articles by query."""

    query: str = Field(
        ..., max_length=300, description="Search query string for Wikipedia articles"
    )
    limit: int = Field(
        10,
        ge=1,
        le=50,
        description="Maximum number of search results to return (1-50)",
    )


class SearchWikipediaResponse(BaseModel):
    """Output schema for Wikipedia search results."""

    results: list[str] = Field(..., description="List of Wikipedia article titles matching the query")


class GetArticleRequest(BaseModel):
    """Input schema for retrieving a Wikipedia article by its exact title."""

    title: str = Field(
        ..., description="Exact title of the Wikipedia article to retrieve"
    )


class ArticleResponse(BaseModel):
    """Output schema representing a Wikipedia article with content and metadata."""

    title: str = Field(..., description="Title of the Wikipedia article")
    summary: str = Field(..., description="Summary of the Wikipedia article")
    text: str = Field(..., description="Full text content of the Wikipedia article")
    url: str = Field(..., description="URL of the Wikipedia article")
    sections: list[str] = Field(..., description="List of section titles in the article")
    links: list[str] = Field(..., description="List of links (article titles) within the article")


class GetSummaryRequest(BaseModel):
    """Input schema for retrieving the summary of a Wikipedia article."""

    title: str = Field(..., description="Title of the Wikipedia article to summarize")


class SummaryResponse(BaseModel):
    """Output schema for Wikipedia article summary."""

    title: str = Field(..., description="Title of the Wikipedia article")
    summary: str = Field(..., description="Summary text of the Wikipedia article")


class GetSectionsRequest(BaseModel):
    """Input schema for retrieving section titles of a Wikipedia article."""

    title: str = Field(
        ..., description="Title of the Wikipedia article to get section titles from"
    )


class SectionsResponse(BaseModel):
    """Output schema for Wikipedia article sections."""

    title: str = Field(..., description="Title of the Wikipedia article")
    sections: list[str] = Field(..., description="List of section titles in the article")


class GetLinksRequest(BaseModel):
    """Input schema for retrieving links within a Wikipedia article."""

    title: str = Field(
        ..., description="Title of the Wikipedia article to get links from"
    )


class LinksResponse(BaseModel):
    """Output schema for links within a Wikipedia article."""

    title: str = Field(..., description="Title of the Wikipedia article")
    links: list[str] = Field(..., description="List of links (article titles) within the article")


class GetRelatedTopicsRequest(BaseModel):
    """Input schema for retrieving topics related to a Wikipedia article."""

    title: str = Field(
        ..., description="Title of the Wikipedia article to get related topics for"
    )
    limit: int = Field(
        20,
        ge=1,
        le=100,
        description="Maximum number of related topics to return",
    )


class RelatedTopicsResponse(BaseModel):
    """Output schema listing topics related to a Wikipedia article."""

    topics: list[str] = Field(..., description="List of related topic titles")


class PricingResponse(BaseModel):
    """Response model for pricing configuration."""

    pricing: dict = Field(description="Pricing data for all endpoints")
    message: str | None = Field(
        default=None, description="Optional message about pricing status"
    )


class HealthCheckResponse(BaseModel):
    """Response model for health check endpoint."""

    status: str = Field(description="Server status")
    service: str = Field(description="Service name")

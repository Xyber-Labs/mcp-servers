from pydantic import BaseModel, Field, model_validator

from mcp_server_arxiv.xy_arxiv.models import ArxivSearchResult


class SearchRequest(BaseModel):
    query: str | None = Field(
        default=None,
        max_length=512,
        description="The search query string for ArXiv. Either 'query' or 'arxiv_id' must be provided.",
    )
    arxiv_id: str | None = Field(
        default=None,
        description="ArXiv paper ID (e.g., '1706.03762' or '2401.00001'). Either 'query' or 'arxiv_id' must be provided.",
    )
    max_results: int | None = Field(
        default=None,
        ge=1,
        le=50,
        description="Optional override for the maximum number of results to fetch and process (1-50)",
    )
    max_text_length: int | None = Field(
        default=None,
        ge=100,
        description="Optional max characters of full text per paper (minimum 100 characters)",
    )

    @model_validator(mode="after")
    def validate_query_or_id(self) -> "SearchRequest":
        if not self.query and not self.arxiv_id:
            raise ValueError("Either 'query' or 'arxiv_id' must be provided.")
        if self.query and self.arxiv_id:
            raise ValueError("Cannot provide both 'query' and 'arxiv_id'. Provide exactly one.")
        return self


class ArxivPaperResponse(BaseModel):
    """Response model for a single ArXiv paper."""

    title: str = Field(description="Title of the paper")
    authors: list[str] = Field(description="List of author names")
    published_date: str = Field(description="Publication date in YYYY-MM-DD format")
    summary: str = Field(description="Abstract/summary of the paper")
    arxiv_id: str = Field(description="ArXiv paper ID")
    pdf_url: str | None = Field(default=None, description="URL to the PDF version")
    full_text: str | None = Field(default=None, description="Extracted full text from PDF (if requested)")
    processing_error: str | None = Field(default=None, description="Error message if PDF processing failed")

    @classmethod
    def from_search_result(cls, result: ArxivSearchResult) -> "ArxivPaperResponse":
        return cls(
            title=result.title,
            authors=result.authors,
            published_date=result.published_date,
            summary=result.summary,
            arxiv_id=result.arxiv_id,
            pdf_url=result.pdf_url,
            full_text=result.full_text,
            processing_error=result.processing_error,
        )

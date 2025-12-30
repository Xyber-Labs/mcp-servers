from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

QueryType = Literal["topic", "profile", "replies"]
SortOrder = Literal["Latest", "Top"]
OutputFormat = Literal["min", "max"]


class TwitterScraperInput(BaseModel):
    """Validated input for Apify tweet scraping actors (default: `apidojo/tweet-scraper`)."""

    model_config = ConfigDict(extra="allow")

    searchTerms: list[str] = Field(min_length=1)
    sort: SortOrder | str = "Latest"
    maxItems: int | None = Field(default=None, ge=1)
    tweetLanguage: str | None = None
    onlyVerifiedUsers: bool | None = None
    onlyImage: bool | None = None
    maxTweets: int | None = Field(default=None, ge=1)


class QueryDefinition(BaseModel):
    """A runnable query (either predefined or custom)."""

    id: str
    type: QueryType
    name: str
    input: TwitterScraperInput
    output: str | None = None

    def output_filename(self) -> str:
        if not self.output:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            first_term = self.input.searchTerms[0] if self.input.searchTerms else "unknown"
            safe = first_term.replace(":", "_").replace(" ", "_")
            return f"twitter_results_{safe}_{timestamp}.json"
        return self.output if self.output.endswith(".json") else f"{self.output}.json"


MinimalTweet = dict[str, Any]


class TwitterData(BaseModel):
    """Container for Twitter data returned by the API."""

    items: list[MinimalTweet]
    query_id: str
    query_name: str

    @classmethod
    def from_api_response(
        cls, response: dict[str, Any], query_id: str = "", query_name: str = ""
    ) -> TwitterData:
        """Create a TwitterData instance from an API response."""
        return cls(
            items=response.get("items", []),
            query_id=query_id,
            query_name=query_name,
        )



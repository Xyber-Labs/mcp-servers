from __future__ import annotations

import hashlib
import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field

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

    @computed_field
    @property
    def cache_key(self) -> str:
        """Deterministic hash key for caching this query."""
        params = self.input.model_dump(exclude_none=True)
        normalized = {
            "type": self.type,
            **{k: v for k, v in sorted(params.items())},
        }
        key_str = json.dumps(normalized, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(key_str.encode("utf-8")).hexdigest()


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

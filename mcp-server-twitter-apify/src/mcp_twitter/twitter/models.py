"""
This module should be changed to reflect the exact shape and units of the twitter data (or other domain data) that your application cares about.

Main responsibility: Provide an immutable data model for twitter information and helpers to construct it from raw API responses.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TwitterData:
    """Immutable twitter data model."""

    items: list[dict[str, Any]]
    query_id: str
    query_name: str

    @classmethod
    def from_api_response(cls, data: dict[str, Any], query_id: str = "", query_name: str = "") -> TwitterData:
        """
        Create a TwitterData instance from API response.

        Args:
            data: Raw API response data from Apify
            query_id: Query identifier
            query_name: Query name

        Returns:
            Structured TwitterData object

        """
        items = data.get("items", []) if isinstance(data, dict) else []
        return cls(
            items=items,
            query_id=query_id,
            query_name=query_name,
        )


import logging
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from mcp_server_lurky.lurky.config import LurkyServiceConfig
from mcp_server_lurky.lurky.errors import (
    LurkyAPIError,
    LurkyAuthError,
    LurkyNotFoundError,
)
from mcp_server_lurky.lurky.models import (
    Discussion,
    MindMap,
    SearchResponse,
    SpaceDetails,
)

logger = logging.getLogger(__name__)


class LurkyClient:
    """Client for interacting with the Lurky API."""

    def __init__(self, config: LurkyServiceConfig):
        self.config = config
        self.headers = {
            "x-lurky-api-key": config.api_key,
            "Accept": "application/json",
        }
        # Ensure base URL is correct and doesn't end with a slash or /docs
        self.base_url = config.base_url.replace("/docs", "").rstrip("/")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        async with httpx.AsyncClient(timeout=self.config.timeout_seconds) as client:
            try:
                response = await client.request(
                    method, url, headers=self.headers, params=params, json=json_data
                )

                if response.status_code == 401:
                    raise LurkyAuthError("Invalid API key", status_code=401)
                elif response.status_code == 404:
                    raise LurkyNotFoundError(
                        f"Resource not found: {url}", status_code=404
                    )

                response.raise_for_status()
                return response.json()

            except (LurkyAuthError, LurkyNotFoundError):
                raise
            except httpx.HTTPStatusError as e:
                logger.error(
                    f"HTTP error occurred: {e.response.status_code} - {e.response.text}"
                )
                raise LurkyAPIError(
                    f"API request failed: {e}",
                    status_code=e.response.status_code,
                    response_text=e.response.text,
                ) from e
            except Exception as e:
                logger.exception(f"Unexpected error during API request: {e}")
                raise LurkyAPIError(f"Unexpected error: {e}") from e

    async def search_discussions(
        self, search_term: str, limit: int = 10, page: int = 0
    ) -> SearchResponse:
        """Search for discussions based on a keyword."""
        data = await self._make_request(
            "GET",
            "discussions/search",
            params={"search_term": search_term, "limit": limit, "page": page},
        )
        return SearchResponse(**data)

    async def get_space_details(self, space_id: str) -> SpaceDetails:
        """Get full details and summary for a specific Space ID."""
        data = await self._make_request("GET", f"spaces/{space_id}")
        return SpaceDetails(**data)

    async def get_space_mind_map(self, space_id: str) -> MindMap:
        """Get the mind map for a specific space."""
        data = await self._make_request("GET", f"spaces/{space_id}/mind-map")
        return MindMap(**data)

    async def get_space_discussions(self, space_id: str) -> list[Discussion]:
        """Get all discussion blocks for a specific space."""
        data = await self._make_request("GET", f"spaces/{space_id}/discussions")
        # The API returns {"discussions": [...]}
        return [Discussion(**d) for d in data.get("discussions", [])]

    async def get_latest_summaries(
        self, topic: str, count: int = 3
    ) -> list[SpaceDetails]:
        """Fetch the latest N unique space summaries for a given topic."""
        search_results = await self.search_discussions(topic, limit=20)

        unique_space_ids = []
        for d in search_results.discussions:
            if d.space_id and d.space_id not in unique_space_ids:
                unique_space_ids.append(d.space_id)
            if len(unique_space_ids) >= count:
                break

        summaries = []
        for sid in unique_space_ids:
            try:
                details = await self.get_space_details(sid)
                # Fetch discussions for these spaces as well
                discussions = await self.get_space_discussions(sid)
                details.discussions = discussions
                summaries.append(details)
            except LurkyNotFoundError:
                continue

        return summaries

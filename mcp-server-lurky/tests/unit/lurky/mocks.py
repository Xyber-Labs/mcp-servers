from __future__ import annotations

from typing import Any


class MockHTTPResponse:
    """Mock HTTPX response for testing."""

    def __init__(
        self,
        payload: dict[str, Any] | None = None,
        status_code: int = 200,
    ):
        self.payload = payload or {}
        self.status_code = status_code
        self.text = str(payload)

    def json(self) -> dict[str, Any]:
        return self.payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            import httpx

            request = httpx.Request("GET", "https://api.lurky.app")
            response = httpx.Response(self.status_code, request=request)
            raise httpx.HTTPStatusError(
                f"Error {self.status_code}", request=request, response=response
            )


class MockLurkyHttpClient:
    """Mock HTTP client that tracks calls and returns predefined responses."""

    def __init__(self, responses: list[MockHTTPResponse] | None = None):
        self.responses = responses or [MockHTTPResponse()]
        self.calls: list[dict[str, Any]] = []
        self._response_index = 0

    async def request(
        self,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> MockHTTPResponse:
        self.calls.append(
            {
                "method": method,
                "url": url,
                "headers": headers,
                "params": params,
                "json": json,
            }
        )

        if self._response_index < len(self.responses):
            resp = self.responses[self._response_index]
            self._response_index += 1
            return resp
        return self.responses[-1]

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


def build_search_response(
    discussions: list[dict[str, Any]] | None = None,
    total: int = 1,
    page: int = 0,
    limit: int = 10,
) -> dict[str, Any]:
    """Build a typical SearchResponse payload."""
    if discussions is None:
        discussions = [
            {
                "id": "disc-123",
                "space_id": "space-456",
                "title": "Test Discussion",
                "summary": "A test discussion about bitcoin",
                "timestamp": 1700000000,
                "coins": [],
                "categories": ["crypto"],
            }
        ]
    return {
        "discussions": discussions,
        "total": total,
        "page": page,
        "limit": limit,
    }


def build_space_details(
    space_id: str = "space-456",
    title: str = "Test Space",
    summary: str = "A test space about crypto",
) -> dict[str, Any]:
    """Build a typical SpaceDetails payload."""
    return {
        "id": space_id,
        "creator_id": "creator-123",
        "creator_handle": "@testuser",
        "title": title,
        "summary": summary,
        "minimized_summary": summary[:50] if len(summary) > 50 else summary,
        "state": "ended",
        "language": "en",
        "overall_sentiment": "positive",
        "participant_count": 100,
        "subscriber_count": 50,
        "likes": 25,
        "categories": ["crypto", "bitcoin"],
        "created_at": 1700000000,
        "started_at": 1700000100,
        "ended_at": 1700001000,
        "discussions": [],
    }


def build_discussions_list(count: int = 2) -> dict[str, Any]:
    """Build a discussions response with multiple items."""
    discussions = []
    for i in range(count):
        discussions.append(
            {
                "id": f"disc-{i}",
                "space_id": "space-456",
                "title": f"Discussion {i}",
                "summary": f"Summary for discussion {i}",
                "timestamp": 1700000000 + i * 100,
                "coins": [],
                "categories": ["crypto"],
            }
        )
    return {"discussions": discussions}


def build_mind_map() -> dict[str, Any]:
    """Build a typical MindMap payload."""
    return {
        "nodes": [
            {
                "id": "node-1",
                "parent_id": None,
                "title": "Main Topic",
                "summary": "The main topic of discussion",
            },
            {
                "id": "node-2",
                "parent_id": "node-1",
                "title": "Subtopic A",
                "summary": "First subtopic",
            },
            {
                "id": "node-3",
                "parent_id": "node-1",
                "title": "Subtopic B",
                "summary": "Second subtopic",
            },
        ]
    }

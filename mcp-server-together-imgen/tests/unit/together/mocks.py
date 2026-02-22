from __future__ import annotations

from typing import Any

import httpx


def build_image_response(
    *,
    b64_json: str = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
    model: str = "black-forest-labs/FLUX.1-dev",
) -> dict[str, Any]:
    """Build a typical Together Images API response."""
    return {
        "data": [
            {
                "b64_json": b64_json,
                "index": 0,
            }
        ],
        "model": model,
        "object": "list",
    }


def build_image_response_with_base64(
    *,
    base64: str = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
) -> dict[str, Any]:
    """Build a response using 'base64' key instead of 'b64_json'."""
    return {
        "data": [
            {
                "base64": base64,
                "index": 0,
            }
        ],
        "object": "list",
    }


def build_image_response_with_url(
    *,
    url: str = "https://example.com/image.png",
) -> dict[str, Any]:
    """Build a response with URL instead of base64 (error case)."""
    return {
        "data": [
            {
                "url": url,
                "index": 0,
            }
        ],
        "object": "list",
    }


def build_chat_completion_response(
    *,
    content: str = "A stunning digital artwork of a cat in space",
    model: str = "deepseek-ai/DeepSeek-V3",
) -> dict[str, Any]:
    """Build a typical Together Chat API response for prompt refinement."""
    return {
        "id": "chatcmpl-test123",
        "object": "chat.completion",
        "created": 1700000000,
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": content,
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 50,
            "completion_tokens": 20,
            "total_tokens": 70,
        },
    }


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
            request = httpx.Request("POST", "https://api.together.xyz")
            response = httpx.Response(self.status_code, request=request)
            raise httpx.HTTPStatusError(
                f"Error {self.status_code}", request=request, response=response
            )


class MockTogetherHttpClient:
    """Mock HTTP client that tracks calls and returns predefined responses."""

    def __init__(self, responses: list[MockHTTPResponse] | None = None):
        self.responses = responses or [MockHTTPResponse()]
        self.calls: list[dict[str, Any]] = []
        self._response_index = 0

    async def post(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
    ) -> MockHTTPResponse:
        self.calls.append(
            {
                "url": url,
                "headers": headers,
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

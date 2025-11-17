from __future__ import annotations

from typing import Any

import httpx

SAMPLE_COORDS = {"lat": "51.5074", "lon": "-0.1278"}


def build_weather_payload(
    *,
    description: str = "clear sky",
    temperature: float = 20.0,
    humidity: int = 55,
) -> dict[str, Any]:
    """Construct a minimal OpenWeatherMap payload."""

    return {
        "weather": [{"description": description}],
        "main": {"temp": temperature, "humidity": humidity},
        "cod": 200,
    }


class MockHTTPResponse:
    """Lightweight stand-in for httpx.Response used in unit tests."""

    def __init__(
        self, *, status_code: int = 200, payload: dict[str, Any] | None = None
    ):
        self.status_code = status_code
        self._payload = payload or build_weather_payload()

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            request = httpx.Request("GET", "https://api.openweathermap.org/weather")
            response = httpx.Response(self.status_code, request=request)
            raise httpx.HTTPStatusError(
                "mock failure", request=request, response=response
            )

    def json(self) -> dict[str, Any]:
        return self._payload


class MockWeatherHttpClient:
    """Simulated httpx.AsyncClient that returns queued responses."""

    def __init__(self, responses: list[MockHTTPResponse] | None = None):
        self.responses = responses or []
        self.calls: list[dict[str, Any]] = []

    async def get(self, url: str, params: dict[str, Any]) -> MockHTTPResponse:
        self.calls.append({"url": url, "params": params})
        if not self.responses:
            raise AssertionError("No mock responses available")
        return self.responses.pop(0)

    async def aclose(self) -> None:
        return

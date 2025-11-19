from __future__ import annotations

import time
from typing import Any, Final

import httpx
import pytest

from mcp_server_weather.weather.config import WeatherConfig
from mcp_server_weather.weather.errors import WeatherApiError, WeatherClientError
from mcp_server_weather.weather.models import WeatherData
from mcp_server_weather.weather.module import WeatherClient

from .mocks import MockHTTPResponse, MockWeatherHttpClient, build_weather_payload

LATITUDE: Final[str] = "51.5074"
LONGITUDE: Final[str] = "-0.1278"
API_KEY: Final[str] = "test-header-key"


@pytest.fixture
def weather_client() -> WeatherClient:
    """Provide a WeatherClient with deterministic configuration for tests."""

    config = WeatherConfig(
        timeout_seconds=1,
        enable_caching=True,
        cache_ttl_seconds=60,
    )
    return WeatherClient(config)


def _attach_http_client(
    monkeypatch: pytest.MonkeyPatch,
    weather_client: WeatherClient,
    http_client: Any,
) -> None:
    def _ensure() -> Any:
        weather_client._client = http_client
        return http_client

    monkeypatch.setattr(weather_client, "_ensure_client", _ensure)
    weather_client._client = http_client


@pytest.mark.asyncio
async def test_get_weather_success(
    monkeypatch: pytest.MonkeyPatch, weather_client: WeatherClient
) -> None:
    payload = build_weather_payload(description="sunny", temperature=18.5, humidity=42)
    http_client = MockWeatherHttpClient([MockHTTPResponse(payload=payload)])
    _attach_http_client(monkeypatch, weather_client, http_client)
    weather_client._client = http_client

    result = await weather_client.get_weather(LATITUDE, LONGITUDE, api_key=API_KEY)

    assert isinstance(result, WeatherData)
    assert result.state == "sunny"
    assert result.temperature == "18.5C"
    assert result.humidity == "42%"
    assert len(http_client.calls) == 1


@pytest.mark.asyncio
async def test_get_weather_uses_cache(
    monkeypatch: pytest.MonkeyPatch, weather_client: WeatherClient
) -> None:
    http_client = MockWeatherHttpClient([MockHTTPResponse()])
    _attach_http_client(monkeypatch, weather_client, http_client)
    weather_client._client = http_client

    await weather_client.get_weather(LATITUDE, LONGITUDE, api_key=API_KEY)
    await weather_client.get_weather(LATITUDE, LONGITUDE, api_key=API_KEY)

    assert len(http_client.calls) == 1


@pytest.mark.asyncio
async def test_cache_expires(
    monkeypatch: pytest.MonkeyPatch, weather_client: WeatherClient
) -> None:
    weather_client.config.cache_ttl_seconds = 1
    payload = build_weather_payload(description="first")
    http_client = MockWeatherHttpClient(
        [
            MockHTTPResponse(payload=payload),
            MockHTTPResponse(payload=build_weather_payload(description="second")),
        ]
    )
    _attach_http_client(monkeypatch, weather_client, http_client)

    initial_time = time.time()
    monkeypatch.setattr(time, "time", lambda: initial_time)
    await weather_client.get_weather(LATITUDE, LONGITUDE, api_key=API_KEY)

    monkeypatch.setattr(time, "time", lambda: initial_time + 2)
    result = await weather_client.get_weather(LATITUDE, LONGITUDE, api_key=API_KEY)

    assert result.state == "second"
    assert len(http_client.calls) == 2


@pytest.mark.asyncio
async def test_http_error_translates_to_weather_api_error(
    monkeypatch: pytest.MonkeyPatch,
    weather_client: WeatherClient,
) -> None:
    class FailingClient:
        async def get(self, url: str, params: dict[str, Any]) -> None:  # type: ignore[override]
            request = httpx.Request("GET", "https://api.openweathermap.org/weather")
            response = httpx.Response(500, request=request)
            raise httpx.HTTPStatusError(
                "mock failure", request=request, response=response
            )

        async def aclose(self) -> None:  # noqa: ANN003
            return None

    failing_client = FailingClient()
    _attach_http_client(monkeypatch, weather_client, failing_client)  # type: ignore[arg-type]
    with pytest.raises(WeatherApiError):
        await weather_client.get_weather(LATITUDE, LONGITUDE, api_key=API_KEY)


@pytest.mark.asyncio
async def test_parsing_error_translates_to_weather_client_error(
    monkeypatch: pytest.MonkeyPatch,
    weather_client: WeatherClient,
) -> None:
    payload = {"main": {"temp": 20}}
    http_client = MockWeatherHttpClient([MockHTTPResponse(payload=payload)])
    _attach_http_client(monkeypatch, weather_client, http_client)

    with pytest.raises(WeatherClientError):
        await weather_client.get_weather(LATITUDE, LONGITUDE, api_key=API_KEY)


@pytest.mark.asyncio
async def test_close_closes_underlying_http_client(
    monkeypatch: pytest.MonkeyPatch,
    weather_client: WeatherClient,
) -> None:
    http_client = MockWeatherHttpClient([MockHTTPResponse()])
    http_client.aclose_called = False

    async def _aclose() -> None:
        http_client.aclose_called = True

    http_client.aclose = _aclose  # type: ignore[method-assign]
    monkeypatch.setattr(weather_client, "_ensure_client", lambda: http_client)
    weather_client._client = http_client

    await weather_client.get_weather(LATITUDE, LONGITUDE, api_key=API_KEY)
    await weather_client.close()

    assert http_client.aclose_called is True


@pytest.mark.asyncio
async def test_get_weather_raises_when_no_api_key_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = WeatherConfig(
        timeout_seconds=1,
        enable_caching=False,
    )
    weather_client = WeatherClient(config)

    http_client = MockWeatherHttpClient([MockHTTPResponse()])
    _attach_http_client(monkeypatch, weather_client, http_client)

    with pytest.raises(WeatherClientError):
        await weather_client.get_weather(LATITUDE, LONGITUDE, api_key="")

    assert http_client.calls == []

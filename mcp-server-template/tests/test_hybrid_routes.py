from __future__ import annotations

import pytest
import pytest_asyncio
from fastapi import FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient

from mcp_server_weather.dependencies import get_weather_client
from mcp_server_weather.hybrid_routers.current_weather import (
    API_KEY_HEADER,
    LocationRequest,
    get_current_weather,
)
from mcp_server_weather.hybrid_routers.current_weather import (
    router as current_router,
)
from mcp_server_weather.hybrid_routers.forecast import (
    get_weather_forecast,
)
from mcp_server_weather.hybrid_routers.forecast import (
    router as forecast_router,
)
from mcp_server_weather.weather.models import WeatherData


class StubWeatherClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, str | None]] = []

    async def get_weather(
        self,
        latitude: str,
        longitude: str,
        units: str | None = None,
        api_key: str = "",
    ) -> WeatherData:
        self.calls.append(
            {
                "latitude": latitude,
                "longitude": longitude,
                "units": units,
                "api_key": api_key,
            }
        )
        return WeatherData(state="clear", temperature="20C", humidity="40%")


@pytest.mark.asyncio
@pytest.mark.parametrize("units", [None, "metric", "imperial"])
async def test_get_current_weather_returns_serialised_weather(
    units: str | None,
) -> None:
    request = LocationRequest(latitude="51.5074", longitude="-0.1278", units=units)
    client = StubWeatherClient()

    result = await get_current_weather(
        location=request,
        weather_api_key="test-header-key",
        weather_client=client,
    )

    assert result == {"state": "clear", "temperature": "20C", "humidity": "40%"}
    assert client.calls[0]["api_key"] == "test-header-key"


@pytest.mark.asyncio
async def test_get_current_weather_uses_header_api_key() -> None:
    request = LocationRequest(latitude="51.5074", longitude="-0.1278", units="metric")
    client = StubWeatherClient()
    api_key = "override-key"

    result = await get_current_weather(
        location=request,
        weather_api_key=api_key,
        weather_client=client,
    )

    assert result == {"state": "clear", "temperature": "20C", "humidity": "40%"}
    assert client.calls[0]["api_key"] == api_key


@pytest.mark.asyncio
async def test_get_current_weather_missing_header_returns_400() -> None:
    request = LocationRequest(latitude="51.5074", longitude="-0.1278", units="metric")
    client = StubWeatherClient()

    with pytest.raises(HTTPException) as exc:
        await get_current_weather(
            location=request,
            weather_api_key="",
            weather_client=client,
        )

    assert exc.value.status_code == 400
    assert API_KEY_HEADER in exc.value.detail


@pytest.mark.asyncio
async def test_get_weather_forecast_returns_forecast_payload() -> None:
    client = StubWeatherClient()
    payload = await get_weather_forecast(days=3, weather_client=client)

    assert payload["location"] == "Sample City"
    assert payload["days"] == 3
    assert len(payload["forecast"]) == 3


@pytest_asyncio.fixture
async def hybrid_client() -> AsyncClient:
    """HTTP-level client for hybrid routers to exercise validation rules."""

    app = FastAPI()
    app.include_router(forecast_router, prefix="/hybrid")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest.mark.asyncio
async def test_current_weather_endpoint_passes_header_to_weather_client() -> None:
    stub_client = StubWeatherClient()
    app = FastAPI()
    app.include_router(current_router, prefix="/hybrid")
    app.dependency_overrides[get_weather_client] = lambda: stub_client

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/hybrid/current",
            json={"latitude": "1.0000", "longitude": "2.0000"},
            headers={API_KEY_HEADER: "header-key"},
        )

    assert response.status_code == 200
    assert stub_client.calls[0]["api_key"] == "header-key"


@pytest.mark.asyncio
@pytest.mark.parametrize("days", [0, 15])
async def test_get_weather_forecast_days_out_of_range_returns_422(
    hybrid_client: AsyncClient, days: int
) -> None:
    response = await hybrid_client.post("/hybrid/forecast", params={"days": days})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_current_weather_empty_body_returns_422() -> None:
    """HTTP-level validation for current weather payload."""

    app = FastAPI()
    app.include_router(current_router, prefix="/hybrid")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/hybrid/current",
            json={},
            headers={API_KEY_HEADER: "test-header-key"},
        )
        assert response.status_code == 422

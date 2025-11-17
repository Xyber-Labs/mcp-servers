from __future__ import annotations

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from mcp_server_weather.hybrid_routers.current_weather import (
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
    async def get_weather(
        self,
        latitude: str,
        longitude: str,
        units: str | None = None,
    ) -> WeatherData:
        return WeatherData(state="clear", temperature="20C", humidity="40%")


@pytest.mark.asyncio
@pytest.mark.parametrize("units", [None, "metric", "imperial"])
async def test_get_current_weather_returns_serialised_weather(
    units: str | None,
) -> None:
    request = LocationRequest(latitude="51.5074", longitude="-0.1278", units=units)
    client = StubWeatherClient()

    result = await get_current_weather(request, weather_client=client)

    assert result == {"state": "clear", "temperature": "20C", "humidity": "40%"}


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
        response = await client.post("/hybrid/current", json={})
        assert response.status_code == 422

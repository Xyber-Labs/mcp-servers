from __future__ import annotations

import pytest

from mcp_server_weather.mcp_routers.analysis import get_weather_analysis
from mcp_server_weather.mcp_routers.geolocation import geolocate_city
from mcp_server_weather.weather.models import WeatherData


class StubWeatherClient:
    async def get_weather(
        self, latitude: str, longitude: str, units: str | None = None, api_key: str = ""
    ) -> WeatherData:
        return WeatherData(state="clear", temperature="20C", humidity="40%")


@pytest.mark.asyncio
async def test_get_weather_analysis_returns_text() -> None:
    response = await get_weather_analysis(
        city="London", weather_client=StubWeatherClient()
    )
    assert "London" in response
    assert "Weather Analysis" in response


@pytest.mark.asyncio
async def test_geolocate_city_returns_coordinates() -> None:
    payload = await geolocate_city("London")
    assert payload["city"] == "London"
    assert "latitude" in payload and "longitude" in payload

"""
E2E smoke tests for hybrid endpoints (accessible via both REST and MCP).

Test coverage:
- /hybrid/current (free endpoint)
- /hybrid/forecast (priced endpoint)
- /hybrid/pricing (free endpoint)
"""

from __future__ import annotations

import pytest

from mcp_server_weather.schemas import (
    ForecastResponse,
    PricingResponse,
    WeatherResponse,
)
from tests.e2e.config import load_e2e_config, require_base_url, require_weather_api_key
from tests.e2e.utils import (
    call_mcp_tool,
    initialize_mcp_session,
    negotiate_mcp_session_id,
    parse_mcp_response,
)

API_KEY_HEADER = "Weather-Api-Key"


# =============================================================================
# /hybrid/current - Free endpoint
# =============================================================================


async def test_hybrid_current_weather_rest(rest_client) -> None:
    """Smoke test: /hybrid/current via REST (always free)."""
    config, client = rest_client
    payload = {"latitude": "51.5074", "longitude": "-0.1278"}
    api_key = require_weather_api_key(config)
    response = await client.post(
        "/hybrid/current",
        json=payload,
        headers={API_KEY_HEADER: api_key},
    )
    assert response.status_code == 200
    weather_data = WeatherResponse(**response.json())
    assert weather_data.state
    assert weather_data.temperature
    assert weather_data.humidity


async def test_hybrid_current_weather_mcp() -> None:
    """Smoke test: current weather via MCP (always free)."""
    config = load_e2e_config()
    require_base_url(config)
    require_weather_api_key(config)

    session_id = await negotiate_mcp_session_id(config)
    await initialize_mcp_session(config, session_id)
    response = await call_mcp_tool(
        config,
        name="get_current_weather",
        arguments={"latitude": "51.5074", "longitude": "-0.1278"},
        session_id=session_id,
    )

    is_error, data = parse_mcp_response(response)
    assert not is_error
    weather_data = WeatherResponse(**data)
    assert weather_data.state
    assert weather_data.temperature
    assert weather_data.humidity


# =============================================================================
# /hybrid/forecast - Priced endpoint
# =============================================================================


@pytest.mark.payment_off
async def test_hybrid_forecast_rest_pricing_off(rest_client) -> None:
    """Priced endpoint works via REST without payment when PRICING_MODE=off."""
    config, client = rest_client
    response = await client.post("/hybrid/forecast", params={"days": 5})
    assert response.status_code == 200
    forecast_data = ForecastResponse(**response.json())
    assert forecast_data.days == 5
    assert isinstance(forecast_data.forecast, list)
    assert len(forecast_data.forecast) > 0


@pytest.mark.payment_on
async def test_hybrid_forecast_rest_no_payment(rest_client) -> None:
    """Priced endpoint returns 402 via REST when PRICING_MODE=on and no payment."""
    config, client = rest_client
    response = await client.post("/hybrid/forecast", params={"days": 5})
    assert response.status_code == 402
    body = response.json()
    assert "accepts" in body and body["accepts"]
    assert body.get("error")


@pytest.mark.payment_on
async def test_hybrid_forecast_rest_with_payment(paid_client) -> None:
    """Priced endpoint succeeds via REST when PRICING_MODE=on and payment provided."""
    config, client = paid_client
    response = await client.post("/hybrid/forecast", params={"days": 5})
    if response.status_code == 402:
        error_body = response.json()
        pytest.fail(
            f"Payment-enabled test received 402 response. "
            f"Payment flow may not be working correctly. "
            f"Error body: {error_body}"
        )
    response.raise_for_status()
    forecast_data = ForecastResponse(**response.json())
    assert forecast_data.days == 5
    assert isinstance(forecast_data.forecast, list)
    assert len(forecast_data.forecast) > 0


@pytest.mark.payment_off
async def test_hybrid_forecast_mcp_pricing_off() -> None:
    """Priced endpoint works via MCP without payment when PRICING_MODE=off."""
    config = load_e2e_config()
    require_base_url(config)

    session_id = await negotiate_mcp_session_id(config)
    await initialize_mcp_session(config, session_id)
    response = await call_mcp_tool(
        config,
        name="get_weather_forecast",
        arguments={"days": 5},
        session_id=session_id,
    )

    is_error, data = parse_mcp_response(response)
    assert not is_error
    forecast_data = ForecastResponse(**data)
    assert forecast_data.days == 5
    assert isinstance(forecast_data.forecast, list)
    assert len(forecast_data.forecast) > 0


@pytest.mark.payment_on
async def test_hybrid_forecast_mcp_no_payment() -> None:
    """Priced endpoint returns 402 via MCP when PRICING_MODE=on and no payment."""
    config = load_e2e_config()
    require_base_url(config)

    session_id = await negotiate_mcp_session_id(config)
    await initialize_mcp_session(config, session_id)
    response = await call_mcp_tool(
        config,
        name="get_weather_forecast",
        arguments={"days": 5},
        session_id=session_id,
    )
    assert response.status_code == 402


@pytest.mark.payment_on
async def test_hybrid_forecast_mcp_with_payment(paid_client) -> None:
    """Priced endpoint succeeds via MCP when PRICING_MODE=on and payment provided."""
    config, client = paid_client

    session_id = await negotiate_mcp_session_id(config, client)
    await initialize_mcp_session(config, session_id, client)
    response = await call_mcp_tool(
        config,
        name="get_weather_forecast",
        arguments={"days": 5},
        session_id=session_id,
        client=client,
    )

    is_error, data = parse_mcp_response(response)
    assert not is_error
    forecast_data = ForecastResponse(**data)
    assert forecast_data.days == 5
    assert isinstance(forecast_data.forecast, list)
    assert len(forecast_data.forecast) > 0


# =============================================================================
# /hybrid/pricing - Free endpoint
# =============================================================================


async def test_hybrid_pricing_rest(rest_client) -> None:
    """Smoke test: /hybrid/pricing via REST (always free)."""
    config, client = rest_client
    response = await client.get("/hybrid/pricing")
    assert response.status_code == 200
    pricing_data = PricingResponse(**response.json())
    assert isinstance(pricing_data.pricing, dict)


async def test_hybrid_pricing_mcp() -> None:
    """Smoke test: pricing info via MCP (always free)."""
    config = load_e2e_config()
    require_base_url(config)

    session_id = await negotiate_mcp_session_id(config)
    await initialize_mcp_session(config, session_id)
    response = await call_mcp_tool(
        config,
        name="weather_get_pricing",
        arguments={},
        session_id=session_id,
    )

    is_error, data = parse_mcp_response(response)
    assert not is_error
    pricing_data = PricingResponse(**data)
    assert isinstance(pricing_data.pricing, dict)

from __future__ import annotations

import pytest

from tests.e2e.config import require_weather_api_key

API_KEY_HEADER = "Weather-Api-Key"


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.payment_agnostic
async def test_hybrid_current_via_rest(rest_client) -> None:
    config, client = rest_client
    payload = {"latitude": "51.5074", "longitude": "-0.1278"}
    api_key = require_weather_api_key(config)
    response = await client.post(
        "/hybrid/current",
        json=payload,
        headers={API_KEY_HEADER: api_key},
    )
    assert response.status_code == 200
    body = response.json()
    assert "state" in body and "temperature" in body and "humidity" in body


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.payment_agnostic
async def test_hybrid_current_via_rest_missing_header_falls_back_to_config(rest_client):
    """Test that missing header falls back to WEATHER_API_KEY config if available."""
    config, client = rest_client
    payload = {"latitude": "51.5074", "longitude": "-0.1278"}
    response = await client.post(
        "/hybrid/current",
        json=payload,
    )
    # If server has WEATHER_API_KEY configured, should work (200)
    # If not, should fail with 503
    if response.status_code == 200:
        body = response.json()
        assert "state" in body and "temperature" in body and "humidity" in body
    else:
        # Server doesn't have config key, so should get 503
        assert response.status_code == 503
        body = response.json()
        assert "not configured" in body.get("detail", "").lower() or "api key" in body.get("detail", "").lower()


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.payment_enabled
async def test_hybrid_forecast_requires_payment(rest_client) -> None:
    config, client = rest_client
    response = await client.post("/hybrid/forecast", params={"days": 5})
    assert response.status_code == 402
    body = response.json()
    assert "accepts" in body and body["accepts"]
    assert body.get("error")


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.payment_enabled
async def test_hybrid_forecast_succeeds_with_x402(paid_client) -> None:
    config, client = paid_client
    response = await client.post("/hybrid/forecast", params={"days": 5})
    if response.status_code == 402:
        error_body = response.json()
        pytest.fail(
            f"Payment-enabled test received 402 response. "
            f"This indicates payment flow is not working correctly. "
            f"Error body: {error_body}"
        )
    response.raise_for_status()
    body = response.json()
    assert body.get("days") == 5
    assert isinstance(body.get("forecast"), list)

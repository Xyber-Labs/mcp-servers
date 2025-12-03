from __future__ import annotations

import pytest

from tests.e2e.config import require_tavily_api_key

API_KEY_HEADER = "Tavily-Api-Key"


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.payment_disabled
async def test_hybrid_search_via_rest(rest_client) -> None:
    config, client = rest_client
    payload = {"query": "Python programming", "max_results": 3}
    api_key = require_tavily_api_key(config)
    response = await client.post(
        "/hybrid/search",
        json=payload,
        headers={API_KEY_HEADER: api_key},
    )
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert len(body) > 0
    assert "title" in body[0]
    assert "url" in body[0]
    assert "content" in body[0]


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.payment_agnostic
async def test_hybrid_search_via_rest_missing_header_falls_back_to_config(rest_client):
    """Test that missing header falls back to TAVILY_API_KEY config if available."""
    config, client = rest_client
    payload = {"query": "Python programming", "max_results": 3}
    response = await client.post(
        "/hybrid/search",
        json=payload,
    )
    # If server has TAVILY_API_KEY configured, should work (200)
    # If not, should fail with 503
    if response.status_code == 200:
        body = response.json()
        assert isinstance(body, list)
    else:
        # Server doesn't have config key, so should get 503
        assert response.status_code == 503
        body = response.json()
        assert "not configured" in body.get("detail", "").lower() or "api key" in body.get("detail", "").lower()


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.payment_agnostic
async def test_hybrid_search_requires_payment(rest_client) -> None:
    config, client = rest_client
    api_key = require_tavily_api_key(config)
    payload = {"query": "Python programming", "max_results": 3}
    response = await client.post(
        "/hybrid/search",
        json=payload,
        headers={API_KEY_HEADER: api_key},
    )
    # This endpoint should require payment (402) or succeed if payment is configured
    if response.status_code == 402:
        body = response.json()
        assert "accepts" in body and body["accepts"]
        assert body.get("error")
    else:
        # If payment is configured, should succeed
        assert response.status_code == 200


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.payment_enabled
async def test_hybrid_search_succeeds_with_x402(paid_client) -> None:
    config, client = paid_client
    api_key = require_tavily_api_key(config)
    payload = {"query": "Python programming", "max_results": 3}
    response = await client.post(
        "/hybrid/search",
        json=payload,
        headers={API_KEY_HEADER: api_key},
    )
    if response.status_code == 402:
        error_body = response.json()
        pytest.fail(f"Httpx client failed to handle 402 response. Error body: {error_body}")
    response.raise_for_status()
    body = response.json()
    assert isinstance(body, list)
    assert len(body) > 0




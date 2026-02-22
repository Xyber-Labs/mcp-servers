"""
E2E smoke tests for hybrid endpoints (accessible via both REST and MCP).

Test coverage:
- /hybrid/search (priced endpoint)
- /hybrid/pricing (free endpoint)
"""

from __future__ import annotations

import pytest

from mcp_server_wikipedia.schemas import PricingResponse, SearchWikipediaResponse

# =============================================================================
# /hybrid/pricing - Free endpoint
# =============================================================================


@pytest.mark.asyncio
async def test_hybrid_pricing_rest(rest_client) -> None:
    """Smoke test: /hybrid/pricing via REST (always free)."""
    config, client = rest_client
    response = await client.get("/hybrid/pricing")
    assert response.status_code == 200
    # Validate response against schema
    pricing_data = PricingResponse(**response.json())
    assert pricing_data.pricing
    assert isinstance(pricing_data.pricing, dict)


# =============================================================================
# /hybrid/search - Priced endpoint
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.payment_off
async def test_hybrid_search_rest_pricing_off(rest_client) -> None:
    """Priced endpoint works via REST without payment when PRICING_MODE=off."""
    config, client = rest_client
    payload = {"query": "Python programming", "limit": 5}
    response = await client.post("/hybrid/search", json=payload)
    assert response.status_code == 200
    # Validate response against schema
    search_data = SearchWikipediaResponse(**response.json())
    assert isinstance(search_data.results, list)
    assert len(search_data.results) > 0


@pytest.mark.asyncio
@pytest.mark.payment_on
async def test_hybrid_search_rest_no_payment(rest_client) -> None:
    """Priced endpoint returns 402 when PRICING_MODE=on and no payment provided."""
    config, client = rest_client
    payload = {"query": "Python programming", "limit": 5}
    response = await client.post("/hybrid/search", json=payload)
    assert response.status_code == 402
    body = response.json()
    assert "accepts" in body and body["accepts"]
    assert body.get("error")


@pytest.mark.asyncio
@pytest.mark.payment_on
async def test_hybrid_search_rest_with_payment(paid_client) -> None:
    """Priced endpoint succeeds when PRICING_MODE=on and payment provided."""
    config, client = paid_client
    payload = {"query": "Python programming", "limit": 5}
    response = await client.post("/hybrid/search", json=payload)
    if response.status_code == 402:
        error_body = response.json()
        pytest.fail(
            f"Payment-enabled test received 402 response. "
            f"Payment flow may not be working correctly. "
            f"Error body: {error_body}"
        )
    response.raise_for_status()
    # Validate response against schema
    search_data = SearchWikipediaResponse(**response.json())
    assert isinstance(search_data.results, list)
    assert len(search_data.results) > 0

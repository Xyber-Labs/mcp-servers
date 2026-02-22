"""
E2E smoke tests for hybrid endpoints (accessible via both REST and MCP).

Test coverage:
- /hybrid/search (priced endpoint)
- /hybrid/pricing (free endpoint)

Payment modes:
- payment_off: Server running with MCP_LURKY_X402_PRICING_MODE=off
- payment_on: Server running with MCP_LURKY_X402_PRICING_MODE=on (requires wallet)
"""

from __future__ import annotations

import pytest

from mcp_server_lurky.schemas import PricingResponse, SearchResponseSchema
from tests.e2e.config import load_e2e_config, require_base_url
from tests.e2e.utils import (
    call_mcp_tool,
    initialize_mcp_session,
    negotiate_mcp_session_id,
    parse_mcp_response,
)

# =============================================================================
# /hybrid/pricing - Free endpoint
# =============================================================================


async def test_hybrid_pricing_rest(rest_client) -> None:
    """Smoke test: /hybrid/pricing via REST (always free)."""
    config, client = rest_client
    response = await client.get("/hybrid/pricing")
    assert response.status_code == 200
    # Validate response against schema
    pricing_data = PricingResponse(**response.json())
    assert pricing_data.pricing
    assert isinstance(pricing_data.pricing, dict)


async def test_hybrid_pricing_mcp() -> None:
    """Smoke test: pricing info via MCP (always free)."""
    config = load_e2e_config()
    require_base_url(config)

    session_id = await negotiate_mcp_session_id(config)
    await initialize_mcp_session(config, session_id)
    response = await call_mcp_tool(
        config,
        name="get_pricing",
        arguments={},
        session_id=session_id,
    )

    is_error, data = parse_mcp_response(response)
    assert not is_error
    pricing_data = PricingResponse(**data)
    assert isinstance(pricing_data.pricing, dict)


# =============================================================================
# /hybrid/search - Priced endpoint
# =============================================================================


@pytest.mark.payment_off
async def test_hybrid_search_rest_pricing_off(rest_client) -> None:
    """Priced endpoint works via REST without payment when PRICING_MODE=off."""
    config, client = rest_client
    params = {"q": "bitcoin", "limit": 10, "page": 0}
    response = await client.get("/hybrid/search", params=params)
    assert response.status_code == 200
    # Validate response against schema
    search_data = SearchResponseSchema(**response.json())
    assert isinstance(search_data.discussions, list)
    assert search_data.total >= 0


@pytest.mark.payment_on
async def test_hybrid_search_rest_no_payment(rest_client) -> None:
    """Priced endpoint returns 402 when PRICING_MODE=on and no payment provided."""
    config, client = rest_client
    params = {"q": "bitcoin", "limit": 10, "page": 0}
    response = await client.get("/hybrid/search", params=params)
    assert response.status_code == 402


@pytest.mark.payment_on
async def test_hybrid_search_rest_with_payment(paid_client) -> None:
    """Priced endpoint succeeds when PRICING_MODE=on and payment provided."""
    config, client = paid_client
    params = {"q": "bitcoin", "limit": 10, "page": 0}
    response = await client.get("/hybrid/search", params=params)
    if response.status_code == 402:
        error_body = response.json()
        pytest.fail(
            f"Payment-enabled test received 402 response. "
            f"Payment flow may not be working correctly. "
            f"Error body: {error_body}"
        )
    response.raise_for_status()
    # Validate response against schema
    search_data = SearchResponseSchema(**response.json())
    assert isinstance(search_data.discussions, list)
    assert search_data.total >= 0


@pytest.mark.payment_off
async def test_hybrid_search_mcp_pricing_off() -> None:
    """Priced endpoint works via MCP without payment when PRICING_MODE=off."""
    config = load_e2e_config()
    require_base_url(config)

    session_id = await negotiate_mcp_session_id(config)
    await initialize_mcp_session(config, session_id)
    response = await call_mcp_tool(
        config,
        name="lurky_search_spaces",
        arguments={"q": "bitcoin", "limit": 10, "page": 0},
        session_id=session_id,
    )

    is_error, data = parse_mcp_response(response)
    assert not is_error
    search_data = SearchResponseSchema(**data)
    assert isinstance(search_data.discussions, list)
    assert search_data.total >= 0


@pytest.mark.payment_on
async def test_hybrid_search_mcp_no_payment() -> None:
    """Priced endpoint returns 402 via MCP when PRICING_MODE=on and no payment."""
    config = load_e2e_config()
    require_base_url(config)

    session_id = await negotiate_mcp_session_id(config)
    await initialize_mcp_session(config, session_id)
    response = await call_mcp_tool(
        config,
        name="lurky_search_spaces",
        arguments={"q": "bitcoin", "limit": 10, "page": 0},
        session_id=session_id,
    )
    assert response.status_code == 402


@pytest.mark.payment_on
async def test_hybrid_search_mcp_with_payment(paid_client) -> None:
    """Priced endpoint succeeds via MCP when PRICING_MODE=on and payment provided."""
    config, client = paid_client

    session_id = await negotiate_mcp_session_id(config, client)
    await initialize_mcp_session(config, session_id, client)
    response = await call_mcp_tool(
        config,
        name="lurky_search_spaces",
        arguments={"q": "bitcoin", "limit": 10, "page": 0},
        session_id=session_id,
        client=client,
    )

    is_error, data = parse_mcp_response(response)
    assert not is_error
    search_data = SearchResponseSchema(**data)
    assert isinstance(search_data.discussions, list)
    assert search_data.total >= 0

"""
E2E smoke tests for hybrid endpoints (accessible via both REST and MCP).

Test coverage:
- /hybrid/search (priced endpoint)
- /hybrid/pricing (free endpoint)
"""

from __future__ import annotations

import pytest

from mcp_server_tavily.schemas import PricingResponse, TavilySearchResultResponse
from tests.e2e.config import load_e2e_config, require_base_url, require_tavily_api_key
from tests.e2e.utils import (
    call_mcp_tool,
    call_mcp_tool_with_client,
    extract_mcp_result,
    get_mcp_content,
    initialize_mcp_session,
    initialize_mcp_session_with_client,
    negotiate_mcp_session_id,
    negotiate_mcp_session_id_with_client,
)

API_KEY_HEADER = "Tavily-Api-Key"


# =============================================================================
# /hybrid/search - Priced endpoint
# =============================================================================


@pytest.mark.asyncio


@pytest.mark.payment_off
async def test_hybrid_search_rest_pricing_off(rest_client) -> None:
    """Priced endpoint works via REST without payment when PRICING_MODE=off."""
    config, client = rest_client
    payload = {"query": "Python programming", "max_results": 3}
    api_key = require_tavily_api_key(config)
    response = await client.post(
        "/hybrid/search",
        json=payload,
        headers={API_KEY_HEADER: api_key},
    )
    assert response.status_code == 200
    # Validate response against schema
    results = response.json()
    assert isinstance(results, list)
    assert len(results) > 0
    # Validate first result against schema
    first_result = TavilySearchResultResponse(**results[0])
    assert first_result.title
    assert first_result.url
    assert first_result.content


@pytest.mark.asyncio


@pytest.mark.payment_on
async def test_hybrid_search_rest_no_payment(rest_client) -> None:
    """Priced endpoint returns 402 via REST when PRICING_MODE=on and no payment."""
    config, client = rest_client
    payload = {"query": "Python programming", "max_results": 3}
    api_key = require_tavily_api_key(config)
    response = await client.post(
        "/hybrid/search",
        json=payload,
        headers={API_KEY_HEADER: api_key},
    )
    assert response.status_code == 402
    body = response.json()
    assert "accepts" in body and body["accepts"]
    assert body.get("error")


@pytest.mark.asyncio


@pytest.mark.payment_on
async def test_hybrid_search_rest_with_payment(paid_client) -> None:
    """Priced endpoint succeeds via REST when PRICING_MODE=on and payment provided."""
    config, client = paid_client
    payload = {"query": "Python programming", "max_results": 3}
    api_key = require_tavily_api_key(config)
    response = await client.post(
        "/hybrid/search",
        json=payload,
        headers={API_KEY_HEADER: api_key},
    )
    if response.status_code == 402:
        error_body = response.json()
        pytest.fail(
            f"Payment-enabled test received 402 response. "
            f"Payment flow may not be working correctly. "
            f"Error body: {error_body}"
        )
    response.raise_for_status()
    # Validate response against schema
    results = response.json()
    assert isinstance(results, list)
    assert len(results) > 0
    # Validate first result against schema
    first_result = TavilySearchResultResponse(**results[0])
    assert first_result.title
    assert first_result.url
    assert first_result.content


@pytest.mark.asyncio


@pytest.mark.payment_off
async def test_hybrid_search_mcp_pricing_off() -> None:
    """Priced endpoint works via MCP without payment when PRICING_MODE=off."""
    config = load_e2e_config()
    require_base_url(config)
    require_tavily_api_key(config)

    session_id = await negotiate_mcp_session_id(config)
    await initialize_mcp_session(config, session_id)
    response = await call_mcp_tool(
        config,
        session_id,
        name="tavily_search",
        arguments={"query": "Python programming", "max_results": 3},
    )
    # Parse MCP response and validate against schema
    result = extract_mcp_result(response)
    assert not result.get("isError", False)
    result_data = get_mcp_content(result)
    assert isinstance(result_data, list)
    assert len(result_data) > 0
    # Validate first result against schema
    first_result = TavilySearchResultResponse(**result_data[0])
    assert first_result.title
    assert first_result.url
    assert first_result.content


@pytest.mark.asyncio


@pytest.mark.payment_on
async def test_hybrid_search_mcp_no_payment() -> None:
    """Priced endpoint returns 402 via MCP when PRICING_MODE=on and no payment."""
    config = load_e2e_config()
    require_base_url(config)
    require_tavily_api_key(config)

    session_id = await negotiate_mcp_session_id(config)
    await initialize_mcp_session(config, session_id)
    response = await call_mcp_tool(
        config,
        session_id,
        name="tavily_search",
        arguments={"query": "Python programming", "max_results": 3},
    )
    assert response.status_code == 402
    body = response.json()
    assert "accepts" in body or "error" in body


@pytest.mark.asyncio


@pytest.mark.payment_on
async def test_hybrid_search_mcp_with_payment(paid_client) -> None:
    """Priced endpoint succeeds via MCP when PRICING_MODE=on and payment provided."""
    config, client = paid_client
    require_tavily_api_key(config)

    session_id = await negotiate_mcp_session_id_with_client(config, client)
    await initialize_mcp_session_with_client(config, client, session_id)
    response = await call_mcp_tool_with_client(
        config,
        client,
        session_id,
        name="tavily_search",
        arguments={"query": "Python programming", "max_results": 3},
    )
    # Parse MCP response and validate against schema
    result = extract_mcp_result(response)
    assert not result.get("isError", False)
    result_data = get_mcp_content(result)
    assert isinstance(result_data, list)
    assert len(result_data) > 0
    # Validate first result against schema
    first_result = TavilySearchResultResponse(**result_data[0])
    assert first_result.title
    assert first_result.url
    assert first_result.content


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
    assert isinstance(pricing_data.pricing, dict)


@pytest.mark.asyncio


async def test_hybrid_pricing_mcp() -> None:
    """Smoke test: pricing info via MCP (always free)."""
    config = load_e2e_config()
    require_base_url(config)

    session_id = await negotiate_mcp_session_id(config)
    await initialize_mcp_session(config, session_id)
    response = await call_mcp_tool(
        config,
        session_id,
        name="tavily_get_pricing",
        arguments={},
    )
    # Parse MCP response and validate against schema
    result = extract_mcp_result(response)
    assert not result.get("isError", False)
    result_data = get_mcp_content(result)
    pricing_data = PricingResponse(**result_data)
    assert isinstance(pricing_data.pricing, dict)

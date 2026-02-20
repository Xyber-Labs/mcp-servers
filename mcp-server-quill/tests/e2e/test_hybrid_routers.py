"""
E2E smoke tests for hybrid endpoints (accessible via both REST and MCP).

Test coverage:
- /hybrid/pricing (free endpoint)
- /hybrid/search/{query} (priced endpoint)
- /hybrid/evm/{query} (priced endpoint)
- /hybrid/solana/{query} (priced endpoint)
"""

from __future__ import annotations

import pytest

from mcp_server_quill.schemas import PricingResponse, TokenSearchResponse, TokenSecurityResponse
from config import load_e2e_config, require_base_url, require_quill_api_key
from utils import (
    call_mcp_tool,
    call_mcp_tool_with_client,
    extract_mcp_result,
    get_mcp_content,
    initialize_mcp_session,
    initialize_mcp_session_with_client,
    negotiate_mcp_session_id,
    negotiate_mcp_session_id_with_client,
)

API_KEY_HEADER = "Quill-Api-Key"


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
        name="quill_get_pricing",
        arguments={},
    )
    # Parse MCP response and validate against schema
    result = extract_mcp_result(response)
    assert not result.get("isError", False)
    result_data = get_mcp_content(result)
    pricing_data = PricingResponse(**result_data)
    assert isinstance(pricing_data.pricing, dict)


# =============================================================================
# /hybrid/search/{query} - Priced endpoint
# =============================================================================


@pytest.mark.asyncio


@pytest.mark.payment_off
async def test_hybrid_search_token_rest_pricing_off(rest_client) -> None:
    """Priced endpoint works via REST without payment when PRICING_MODE=off."""
    config, client = rest_client
    response = await client.get("/hybrid/search/WETH", params={"chain": "ethereum"})
    assert response.status_code == 200
    # Validate response against schema
    search_data = TokenSearchResponse(**response.json())
    assert search_data.symbol == "WETH"
    assert search_data.chainId == "ethereum"


@pytest.mark.asyncio


@pytest.mark.payment_on
async def test_hybrid_search_token_rest_no_payment(rest_client) -> None:
    """Priced endpoint returns 402 via REST when PRICING_MODE=on and no payment."""
    config, client = rest_client
    response = await client.get("/hybrid/search/WETH", params={"chain": "ethereum"})
    assert response.status_code == 402
    body = response.json()
    assert "accepts" in body and body["accepts"]
    assert body.get("error")


@pytest.mark.asyncio


@pytest.mark.payment_on
async def test_hybrid_search_token_rest_with_payment(paid_client) -> None:
    """Priced endpoint succeeds via REST when PRICING_MODE=on and payment provided."""
    config, client = paid_client
    response = await client.get("/hybrid/search/WETH", params={"chain": "ethereum"})
    if response.status_code == 402:
        error_body = response.json()
        pytest.fail(
            f"Payment-enabled test received 402 response. "
            f"Payment flow may not be working correctly. "
            f"Error body: {error_body}"
        )
    response.raise_for_status()
    # Validate response against schema
    search_data = TokenSearchResponse(**response.json())
    assert search_data.symbol == "WETH"
    assert search_data.chainId == "ethereum"


@pytest.mark.asyncio


@pytest.mark.payment_off
async def test_hybrid_search_token_mcp_pricing_off() -> None:
    """Priced endpoint works via MCP without payment when PRICING_MODE=off."""
    config = load_e2e_config()
    require_base_url(config)

    session_id = await negotiate_mcp_session_id(config)
    await initialize_mcp_session(config, session_id)
    response = await call_mcp_tool(
        config,
        session_id,
        name="search_token_address",
        arguments={"query": "WETH", "chain": "ethereum"},
    )
    # Parse MCP response and validate against schema
    result = extract_mcp_result(response)
    assert not result.get("isError", False)
    result_data = get_mcp_content(result)
    search_data = TokenSearchResponse(**result_data)
    assert search_data.symbol == "WETH"
    assert search_data.chainId == "ethereum"


@pytest.mark.asyncio


@pytest.mark.payment_on
async def test_hybrid_search_token_mcp_no_payment() -> None:
    """Priced endpoint returns 402 via MCP when PRICING_MODE=on and no payment."""
    config = load_e2e_config()
    require_base_url(config)

    session_id = await negotiate_mcp_session_id(config)
    await initialize_mcp_session(config, session_id)
    response = await call_mcp_tool(
        config,
        session_id,
        name="search_token_address",
        arguments={"query": "WETH", "chain": "ethereum"},
    )
    assert response.status_code == 402
    body = response.json()
    assert "accepts" in body or "error" in body


@pytest.mark.asyncio


@pytest.mark.payment_on
async def test_hybrid_search_token_mcp_with_payment(paid_client) -> None:
    """Priced endpoint succeeds via MCP when PRICING_MODE=on and payment provided."""
    config, client = paid_client

    session_id = await negotiate_mcp_session_id_with_client(config, client)
    await initialize_mcp_session_with_client(config, client, session_id)
    response = await call_mcp_tool_with_client(
        config,
        client,
        session_id,
        name="search_token_address",
        arguments={"query": "WETH", "chain": "ethereum"},
    )
    # Parse MCP response and validate against schema
    result = extract_mcp_result(response)
    assert not result.get("isError", False)
    result_data = get_mcp_content(result)
    search_data = TokenSearchResponse(**result_data)
    assert search_data.symbol == "WETH"
    assert search_data.chainId == "ethereum"


# =============================================================================
# /hybrid/evm/{query} - Priced endpoint
# =============================================================================


@pytest.mark.asyncio


@pytest.mark.payment_off
async def test_hybrid_evm_token_info_rest_pricing_off(rest_client) -> None:
    """Priced endpoint works via REST without payment when PRICING_MODE=off."""
    config, client = rest_client
    api_key = require_quill_api_key(config)
    response = await client.get(
        "/hybrid/evm/WETH",
        headers={API_KEY_HEADER: api_key},
        params={"quill_chain_id": "1"},
    )
    assert response.status_code == 200
    # Validate response against schema
    token_data = TokenSecurityResponse(**response.json())
    assert token_data.search_result.symbol == "WETH"
    assert isinstance(token_data.quill_data, dict)


@pytest.mark.asyncio


@pytest.mark.payment_on
async def test_hybrid_evm_token_info_rest_no_payment(rest_client) -> None:
    """Priced endpoint returns 402 via REST when PRICING_MODE=on and no payment."""
    config, client = rest_client
    api_key = require_quill_api_key(config)
    response = await client.get(
        "/hybrid/evm/WETH",
        headers={API_KEY_HEADER: api_key},
        params={"quill_chain_id": "1"},
    )
    assert response.status_code == 402
    body = response.json()
    assert "accepts" in body and body["accepts"]
    assert body.get("error")


@pytest.mark.asyncio


@pytest.mark.payment_on
async def test_hybrid_evm_token_info_rest_with_payment(paid_client) -> None:
    """Priced endpoint succeeds via REST when PRICING_MODE=on and payment provided."""
    config, client = paid_client
    api_key = require_quill_api_key(config)
    response = await client.get(
        "/hybrid/evm/WETH",
        headers={API_KEY_HEADER: api_key},
        params={"quill_chain_id": "1"},
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
    token_data = TokenSecurityResponse(**response.json())
    assert token_data.search_result.symbol == "WETH"
    assert isinstance(token_data.quill_data, dict)


@pytest.mark.asyncio


@pytest.mark.payment_off
async def test_hybrid_evm_token_info_mcp_pricing_off() -> None:
    """Priced endpoint works via MCP without payment when PRICING_MODE=off."""
    config = load_e2e_config()
    require_base_url(config)

    session_id = await negotiate_mcp_session_id(config)
    await initialize_mcp_session(config, session_id)
    response = await call_mcp_tool(
        config,
        session_id,
        name="get_evm_token_info",
        arguments={"query": "WETH", "quill_chain_id": "1"},
    )
    # Parse MCP response and validate against schema
    result = extract_mcp_result(response)
    assert not result.get("isError", False)
    result_data = get_mcp_content(result)
    token_data = TokenSecurityResponse(**result_data)
    assert token_data.search_result.symbol == "WETH"
    assert isinstance(token_data.quill_data, dict)


@pytest.mark.asyncio


@pytest.mark.payment_on
async def test_hybrid_evm_token_info_mcp_no_payment() -> None:
    """Priced endpoint returns 402 via MCP when PRICING_MODE=on and no payment."""
    config = load_e2e_config()
    require_base_url(config)

    session_id = await negotiate_mcp_session_id(config)
    await initialize_mcp_session(config, session_id)
    response = await call_mcp_tool(
        config,
        session_id,
        name="get_evm_token_info",
        arguments={"query": "WETH", "quill_chain_id": "1"},
    )
    assert response.status_code == 402
    body = response.json()
    assert "accepts" in body or "error" in body


@pytest.mark.asyncio


@pytest.mark.payment_on
async def test_hybrid_evm_token_info_mcp_with_payment(paid_client) -> None:
    """Priced endpoint succeeds via MCP when PRICING_MODE=on and payment provided."""
    config, client = paid_client

    session_id = await negotiate_mcp_session_id_with_client(config, client)
    await initialize_mcp_session_with_client(config, client, session_id)
    response = await call_mcp_tool_with_client(
        config,
        client,
        session_id,
        name="get_evm_token_info",
        arguments={"query": "WETH", "quill_chain_id": "1"},
    )
    # Parse MCP response and validate against schema
    result = extract_mcp_result(response)
    assert not result.get("isError", False)
    result_data = get_mcp_content(result)
    token_data = TokenSecurityResponse(**result_data)
    assert token_data.search_result.symbol == "WETH"
    assert isinstance(token_data.quill_data, dict)


# =============================================================================
# /hybrid/solana/{query} - Priced endpoint
# =============================================================================


@pytest.mark.asyncio


@pytest.mark.payment_off
async def test_hybrid_solana_token_info_rest_pricing_off(rest_client) -> None:
    """Priced endpoint works via REST without payment when PRICING_MODE=off."""
    config, client = rest_client
    api_key = require_quill_api_key(config)
    response = await client.get(
        "/hybrid/solana/RAY",
        headers={API_KEY_HEADER: api_key},
    )
    assert response.status_code == 200
    # Validate response against schema
    token_data = TokenSecurityResponse(**response.json())
    assert token_data.search_result.symbol == "RAY"
    assert token_data.search_result.chainId == "solana"
    assert isinstance(token_data.quill_data, dict)


@pytest.mark.asyncio


@pytest.mark.payment_on
async def test_hybrid_solana_token_info_rest_no_payment(rest_client) -> None:
    """Priced endpoint returns 402 via REST when PRICING_MODE=on and no payment."""
    config, client = rest_client
    api_key = require_quill_api_key(config)
    response = await client.get(
        "/hybrid/solana/RAY",
        headers={API_KEY_HEADER: api_key},
    )
    assert response.status_code == 402
    body = response.json()
    assert "accepts" in body and body["accepts"]
    assert body.get("error")


@pytest.mark.asyncio


@pytest.mark.payment_on
async def test_hybrid_solana_token_info_rest_with_payment(paid_client) -> None:
    """Priced endpoint succeeds via REST when PRICING_MODE=on and payment provided."""
    config, client = paid_client
    api_key = require_quill_api_key(config)
    response = await client.get(
        "/hybrid/solana/RAY",
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
    token_data = TokenSecurityResponse(**response.json())
    assert token_data.search_result.symbol == "RAY"
    assert token_data.search_result.chainId == "solana"
    assert isinstance(token_data.quill_data, dict)


@pytest.mark.asyncio


@pytest.mark.payment_off
async def test_hybrid_solana_token_info_mcp_pricing_off() -> None:
    """Priced endpoint works via MCP without payment when PRICING_MODE=off."""
    config = load_e2e_config()
    require_base_url(config)

    session_id = await negotiate_mcp_session_id(config)
    await initialize_mcp_session(config, session_id)
    response = await call_mcp_tool(
        config,
        session_id,
        name="get_solana_token_info",
        arguments={"query": "RAY"},
    )
    # Parse MCP response and validate against schema
    result = extract_mcp_result(response)
    assert not result.get("isError", False)
    result_data = get_mcp_content(result)
    token_data = TokenSecurityResponse(**result_data)
    assert token_data.search_result.symbol == "RAY"
    assert token_data.search_result.chainId == "solana"
    assert isinstance(token_data.quill_data, dict)


@pytest.mark.asyncio


@pytest.mark.payment_on
async def test_hybrid_solana_token_info_mcp_no_payment() -> None:
    """Priced endpoint returns 402 via MCP when PRICING_MODE=on and no payment."""
    config = load_e2e_config()
    require_base_url(config)

    session_id = await negotiate_mcp_session_id(config)
    await initialize_mcp_session(config, session_id)
    response = await call_mcp_tool(
        config,
        session_id,
        name="get_solana_token_info",
        arguments={"query": "RAY"},
    )
    assert response.status_code == 402
    body = response.json()
    assert "accepts" in body or "error" in body


@pytest.mark.asyncio


@pytest.mark.payment_on
async def test_hybrid_solana_token_info_mcp_with_payment(paid_client) -> None:
    """Priced endpoint succeeds via MCP when PRICING_MODE=on and payment provided."""
    config, client = paid_client

    session_id = await negotiate_mcp_session_id_with_client(config, client)
    await initialize_mcp_session_with_client(config, client, session_id)
    response = await call_mcp_tool_with_client(
        config,
        client,
        session_id,
        name="get_solana_token_info",
        arguments={"query": "RAY"},
    )
    # Parse MCP response and validate against schema
    result = extract_mcp_result(response)
    assert not result.get("isError", False)
    result_data = get_mcp_content(result)
    token_data = TokenSecurityResponse(**result_data)
    assert token_data.search_result.symbol == "RAY"
    assert token_data.search_result.chainId == "solana"
    assert isinstance(token_data.quill_data, dict)

"""
E2E smoke tests for hybrid endpoints (accessible via both REST and MCP).

Test coverage:
- /hybrid/parse-gitbook (priced endpoint)
- /hybrid/parse-github (priced endpoint)
- /hybrid/pricing (free endpoint)

Note: For simplicity, we test parse-gitbook since both parse endpoints have similar pricing.
"""

from __future__ import annotations

import pytest

from mcp_server_gitparser.schemas import ConvertResponse, PricingResponse
from e2e.config import load_e2e_config, require_base_url
from e2e.utils import (
    call_mcp_tool,
    call_mcp_tool_with_client,
    initialize_mcp_session,
    initialize_mcp_session_with_client,
    negotiate_mcp_session_id,
    negotiate_mcp_session_id_with_client,
    parse_mcp_response,
)


# =============================================================================
# /hybrid/parse-gitbook - Priced endpoint
# =============================================================================


@pytest.mark.asyncio


@pytest.mark.payment_off
async def test_hybrid_parse_gitbook_rest_pricing_off(rest_client) -> None:
    """Priced endpoint works via REST without payment when PRICING_MODE=off."""
    config, client = rest_client
    payload = {"url": "https://docs.gitbook.com"}
    response = await client.post("/hybrid/parse-gitbook", json=payload)
    assert response.status_code == 200
    # Validate response against schema
    convert_data = ConvertResponse(**response.json())
    assert convert_data.success is True
    assert convert_data.markdown
    assert len(convert_data.markdown) > 0


@pytest.mark.asyncio


@pytest.mark.payment_on
async def test_hybrid_parse_gitbook_rest_no_payment(rest_client) -> None:
    """Priced endpoint returns 402 via REST when PRICING_MODE=on and no payment."""
    config, client = rest_client
    payload = {"url": "https://docs.gitbook.com"}
    response = await client.post("/hybrid/parse-gitbook", json=payload)
    assert response.status_code == 402
    body = response.json()
    assert "accepts" in body and body["accepts"]
    assert body.get("error")


@pytest.mark.asyncio


@pytest.mark.payment_on
async def test_hybrid_parse_gitbook_rest_with_payment(paid_client) -> None:
    """Priced endpoint succeeds via REST when PRICING_MODE=on and payment provided."""
    config, client = paid_client
    payload = {"url": "https://docs.gitbook.com"}
    response = await client.post("/hybrid/parse-gitbook", json=payload)
    if response.status_code == 402:
        error_body = response.json()
        pytest.fail(
            f"Payment-enabled test received 402 response. "
            f"Payment flow may not be working correctly. "
            f"Error body: {error_body}"
        )
    response.raise_for_status()
    # Validate response against schema
    convert_data = ConvertResponse(**response.json())
    assert convert_data.success is True
    assert convert_data.markdown
    assert len(convert_data.markdown) > 0


@pytest.mark.asyncio


@pytest.mark.payment_off
async def test_hybrid_parse_gitbook_mcp_pricing_off() -> None:
    """Priced endpoint works via MCP without payment when PRICING_MODE=off."""
    config = load_e2e_config()
    require_base_url(config)

    session_id = await negotiate_mcp_session_id(config)
    await initialize_mcp_session(config, session_id)
    response = await call_mcp_tool(
        config,
        session_id,
        name="parse_gitbook",
        arguments={"url": "https://docs.gitbook.com"},
    )
    # Parse MCP response and validate against schema
    result_data = parse_mcp_response(response)
    convert_data = ConvertResponse(**result_data)
    assert convert_data.success is True
    assert convert_data.markdown
    assert len(convert_data.markdown) > 0


@pytest.mark.asyncio


@pytest.mark.payment_on
async def test_hybrid_parse_gitbook_mcp_no_payment() -> None:
    """Priced endpoint returns 402 via MCP when PRICING_MODE=on and no payment."""
    config = load_e2e_config()
    require_base_url(config)

    session_id = await negotiate_mcp_session_id(config)
    await initialize_mcp_session(config, session_id)
    response = await call_mcp_tool(
        config,
        session_id,
        name="parse_gitbook",
        arguments={"url": "https://docs.gitbook.com"},
    )
    assert response.status_code == 402
    body = response.json()
    assert "accepts" in body or "error" in body


@pytest.mark.asyncio


@pytest.mark.payment_on
async def test_hybrid_parse_gitbook_mcp_with_payment(paid_client) -> None:
    """Priced endpoint succeeds via MCP when PRICING_MODE=on and payment provided."""
    config, client = paid_client

    session_id = await negotiate_mcp_session_id_with_client(config, client)
    await initialize_mcp_session_with_client(config, client, session_id)
    response = await call_mcp_tool_with_client(
        config,
        client,
        session_id,
        name="parse_gitbook",
        arguments={"url": "https://docs.gitbook.com"},
    )
    # Parse MCP response and validate against schema
    result_data = parse_mcp_response(response)
    convert_data = ConvertResponse(**result_data)
    assert convert_data.success is True
    assert convert_data.markdown
    assert len(convert_data.markdown) > 0


# =============================================================================
# /hybrid/parse-github - Priced endpoint (similar to parse-gitbook)
# =============================================================================


@pytest.mark.asyncio


@pytest.mark.payment_off
async def test_hybrid_parse_github_rest_pricing_off(rest_client) -> None:
    """Priced endpoint works via REST without payment when PRICING_MODE=off."""
    config, client = rest_client
    payload = {
        "url": "https://github.com/modelcontextprotocol/python-sdk",
        "token": None,
        "include_submodules": False,
        "include_gitignored": False,
    }
    response = await client.post("/hybrid/parse-github", json=payload)
    assert response.status_code == 200
    # Validate response against schema
    convert_data = ConvertResponse(**response.json())
    assert convert_data.success is True
    assert convert_data.markdown
    assert len(convert_data.markdown) > 0


@pytest.mark.asyncio


@pytest.mark.payment_on
async def test_hybrid_parse_github_rest_no_payment(rest_client) -> None:
    """Priced endpoint returns 402 via REST when PRICING_MODE=on and no payment."""
    config, client = rest_client
    payload = {
        "url": "https://github.com/modelcontextprotocol/python-sdk",
        "token": None,
        "include_submodules": False,
        "include_gitignored": False,
    }
    response = await client.post("/hybrid/parse-github", json=payload)
    assert response.status_code == 402
    body = response.json()
    assert "accepts" in body and body["accepts"]
    assert body.get("error")


@pytest.mark.asyncio


@pytest.mark.payment_on
async def test_hybrid_parse_github_rest_with_payment(paid_client) -> None:
    """Priced endpoint succeeds via REST when PRICING_MODE=on and payment provided."""
    config, client = paid_client
    payload = {
        "url": "https://github.com/modelcontextprotocol/python-sdk",
        "token": None,
        "include_submodules": False,
        "include_gitignored": False,
    }
    response = await client.post("/hybrid/parse-github", json=payload)
    if response.status_code == 402:
        error_body = response.json()
        pytest.fail(
            f"Payment-enabled test received 402 response. "
            f"Payment flow may not be working correctly. "
            f"Error body: {error_body}"
        )
    response.raise_for_status()
    # Validate response against schema
    convert_data = ConvertResponse(**response.json())
    assert convert_data.success is True
    assert convert_data.markdown
    assert len(convert_data.markdown) > 0


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
        name="gitparser_get_pricing",
        arguments={},
    )
    # Parse MCP response and validate against schema
    result_data = parse_mcp_response(response)
    pricing_data = PricingResponse(**result_data)
    assert isinstance(pricing_data.pricing, dict)

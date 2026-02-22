"""
E2E smoke tests for hybrid endpoints (accessible via both REST and MCP).

Test coverage:
- /api/health (free endpoint)
- /hybrid/v1/search/topic (priced endpoint)
- /hybrid/v1/search/profile (priced endpoint - consolidated, supports single/batch)
- /hybrid/v1/search/replies (priced endpoint)

Payment modes:
- payment_off: Server running with MCP_TWITTER_X402_PRICING_MODE=off
- payment_on: Server running with MCP_TWITTER_X402_PRICING_MODE=on (requires wallet)
"""

from __future__ import annotations

import pytest

from tests.e2e.config import load_e2e_config, require_base_url
from tests.e2e.utils import (
    call_mcp_tool,
    initialize_mcp_session,
    negotiate_mcp_session_id,
    parse_mcp_response,
)

# =============================================================================
# /api/health - Free endpoint (no payment required)
# =============================================================================


async def test_health_rest(rest_client) -> None:
    """GET /api/health returns 200 OK (always free)."""
    config, client = rest_client
    response = await client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "service" in data


# =============================================================================
# /hybrid/v1/search/topic - Priced endpoint
# =============================================================================


@pytest.mark.payment_off
async def test_search_topic_rest_pricing_off(rest_client) -> None:
    """Priced endpoint works via REST without payment when PRICING_MODE=off."""
    config, client = rest_client
    response = await client.post(
        "/hybrid/v1/search/topic",
        json={"topic": "python programming", "max_items": 5},
    )
    assert response.status_code == 200


@pytest.mark.payment_on
async def test_search_topic_rest_no_payment(rest_client) -> None:
    """Priced endpoint returns 402 via REST when PRICING_MODE=on and no payment."""
    config, client = rest_client
    response = await client.post(
        "/hybrid/v1/search/topic",
        json={"topic": "python programming", "max_items": 5},
    )
    assert response.status_code == 402


@pytest.mark.payment_on
async def test_search_topic_rest_with_payment(paid_client) -> None:
    """Priced endpoint succeeds via REST when PRICING_MODE=on and payment provided."""
    config, client = paid_client
    response = await client.post(
        "/hybrid/v1/search/topic",
        json={"topic": "python programming", "max_items": 5},
    )
    assert response.status_code == 200


@pytest.mark.payment_off
async def test_search_topic_mcp_pricing_off() -> None:
    """Priced endpoint works via MCP without payment when PRICING_MODE=off."""
    config = load_e2e_config()
    require_base_url(config)

    session_id = await negotiate_mcp_session_id(config)
    await initialize_mcp_session(config, session_id)
    response = await call_mcp_tool(
        config,
        name="search_topic",
        arguments={"topic": "python programming", "max_items": 5},
        session_id=session_id,
    )
    is_error, _ = parse_mcp_response(response)
    assert not is_error


@pytest.mark.payment_on
async def test_search_topic_mcp_no_payment() -> None:
    """Priced endpoint returns 402 via MCP when PRICING_MODE=on and no payment."""
    config = load_e2e_config()
    require_base_url(config)

    session_id = await negotiate_mcp_session_id(config)
    await initialize_mcp_session(config, session_id)
    response = await call_mcp_tool(
        config,
        name="search_topic",
        arguments={"topic": "python programming", "max_items": 5},
        session_id=session_id,
    )
    assert response.status_code == 402


@pytest.mark.payment_on
async def test_search_topic_mcp_with_payment(paid_client) -> None:
    """Priced endpoint succeeds via MCP when PRICING_MODE=on and payment provided."""
    config, client = paid_client

    session_id = await negotiate_mcp_session_id(config, client)
    await initialize_mcp_session(config, session_id, client)
    response = await call_mcp_tool(
        config,
        name="search_topic",
        arguments={"topic": "python programming", "max_items": 5},
        session_id=session_id,
        client=client,
    )
    is_error, _ = parse_mcp_response(response)
    assert not is_error


@pytest.mark.payment_off
async def test_search_topic_missing_topic_returns_422(rest_client) -> None:
    """POST without required 'topic' field returns 422 (only when payment is off)."""
    config, client = rest_client
    response = await client.post(
        "/hybrid/v1/search/topic",
        json={"max_items": 10},
    )
    assert response.status_code == 422


# =============================================================================
# /hybrid/v1/search/profile - Priced endpoint (consolidated)
# Supports: single user, multiple users, with/without date filters
# =============================================================================


@pytest.mark.payment_off
async def test_search_profile_single_rest_pricing_off(rest_client) -> None:
    """Single user profile search works via REST when PRICING_MODE=off."""
    config, client = rest_client
    response = await client.post(
        "/hybrid/v1/search/profile",
        json={"usernames": ["elonmusk"], "max_items": 5},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["username"] == "elonmusk"


@pytest.mark.payment_off
async def test_search_profile_batch_rest_pricing_off(rest_client) -> None:
    """Multiple user profile search works via REST when PRICING_MODE=off."""
    config, client = rest_client
    response = await client.post(
        "/hybrid/v1/search/profile",
        json={"usernames": ["elonmusk", "jack"], "max_items": 3},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


@pytest.mark.payment_off
async def test_search_profile_with_dates_rest_pricing_off(rest_client) -> None:
    """Profile search with date filters works via REST when PRICING_MODE=off."""
    config, client = rest_client
    response = await client.post(
        "/hybrid/v1/search/profile",
        json={
            "usernames": ["elonmusk"],
            "max_items": 5,
            "from_date": "2025-01-01",
            "to_date": "2025-01-31",
        },
    )
    assert response.status_code == 200


@pytest.mark.payment_on
async def test_search_profile_rest_no_payment(rest_client) -> None:
    """Priced endpoint returns 402 via REST when PRICING_MODE=on and no payment."""
    config, client = rest_client
    response = await client.post(
        "/hybrid/v1/search/profile",
        json={"usernames": ["elonmusk"], "max_items": 5},
    )
    assert response.status_code == 402


@pytest.mark.payment_on
async def test_search_profile_rest_with_payment(paid_client) -> None:
    """Priced endpoint succeeds via REST when PRICING_MODE=on and payment provided."""
    config, client = paid_client
    response = await client.post(
        "/hybrid/v1/search/profile",
        json={"usernames": ["elonmusk"], "max_items": 5},
    )
    assert response.status_code == 200


@pytest.mark.payment_off
async def test_search_profile_mcp_pricing_off() -> None:
    """Priced endpoint works via MCP without payment when PRICING_MODE=off."""
    config = load_e2e_config()
    require_base_url(config)

    session_id = await negotiate_mcp_session_id(config)
    await initialize_mcp_session(config, session_id)
    response = await call_mcp_tool(
        config,
        name="search_profile",
        arguments={"usernames": ["elonmusk"], "max_items": 5},
        session_id=session_id,
    )
    is_error, _ = parse_mcp_response(response)
    assert not is_error


@pytest.mark.payment_on
async def test_search_profile_mcp_no_payment() -> None:
    """Priced endpoint returns 402 via MCP when PRICING_MODE=on and no payment."""
    config = load_e2e_config()
    require_base_url(config)

    session_id = await negotiate_mcp_session_id(config)
    await initialize_mcp_session(config, session_id)
    response = await call_mcp_tool(
        config,
        name="search_profile",
        arguments={"usernames": ["elonmusk"], "max_items": 5},
        session_id=session_id,
    )
    assert response.status_code == 402


@pytest.mark.payment_on
async def test_search_profile_mcp_with_payment(paid_client) -> None:
    """Priced endpoint succeeds via MCP when PRICING_MODE=on and payment provided."""
    config, client = paid_client

    session_id = await negotiate_mcp_session_id(config, client)
    await initialize_mcp_session(config, session_id, client)
    response = await call_mcp_tool(
        config,
        name="search_profile",
        arguments={"usernames": ["elonmusk"], "max_items": 5},
        session_id=session_id,
        client=client,
    )
    is_error, _ = parse_mcp_response(response)
    assert not is_error


@pytest.mark.payment_off
async def test_search_profile_empty_usernames_returns_422(rest_client) -> None:
    """POST with empty usernames list returns 422 (only when payment is off)."""
    config, client = rest_client
    response = await client.post(
        "/hybrid/v1/search/profile",
        json={"usernames": []},
    )
    assert response.status_code == 422


# =============================================================================
# /hybrid/v1/search/replies - Priced endpoint
# =============================================================================


@pytest.mark.payment_off
async def test_search_replies_rest_pricing_off(rest_client) -> None:
    """Priced endpoint works via REST without payment when PRICING_MODE=off."""
    config, client = rest_client
    response = await client.post(
        "/hybrid/v1/search/replies",
        json={"conversation_id": "1234567890", "max_items": 5},
    )
    assert response.status_code == 200


@pytest.mark.payment_on
async def test_search_replies_rest_no_payment(rest_client) -> None:
    """Priced endpoint returns 402 via REST when PRICING_MODE=on and no payment."""
    config, client = rest_client
    response = await client.post(
        "/hybrid/v1/search/replies",
        json={"conversation_id": "1234567890", "max_items": 5},
    )
    assert response.status_code == 402


@pytest.mark.payment_on
async def test_search_replies_rest_with_payment(paid_client) -> None:
    """Priced endpoint succeeds via REST when PRICING_MODE=on and payment provided."""
    config, client = paid_client
    response = await client.post(
        "/hybrid/v1/search/replies",
        json={"conversation_id": "1234567890", "max_items": 5},
    )
    assert response.status_code == 200


@pytest.mark.payment_off
async def test_search_replies_mcp_pricing_off() -> None:
    """Priced endpoint works via MCP without payment when PRICING_MODE=off."""
    config = load_e2e_config()
    require_base_url(config)

    session_id = await negotiate_mcp_session_id(config)
    await initialize_mcp_session(config, session_id)
    response = await call_mcp_tool(
        config,
        name="search_replies",
        arguments={"conversation_id": "1234567890", "max_items": 5},
        session_id=session_id,
    )
    is_error, _ = parse_mcp_response(response)
    assert not is_error


@pytest.mark.payment_on
async def test_search_replies_mcp_no_payment() -> None:
    """Priced endpoint returns 402 via MCP when PRICING_MODE=on and no payment."""
    config = load_e2e_config()
    require_base_url(config)

    session_id = await negotiate_mcp_session_id(config)
    await initialize_mcp_session(config, session_id)
    response = await call_mcp_tool(
        config,
        name="search_replies",
        arguments={"conversation_id": "1234567890", "max_items": 5},
        session_id=session_id,
    )
    assert response.status_code == 402


@pytest.mark.payment_on
async def test_search_replies_mcp_with_payment(paid_client) -> None:
    """Priced endpoint succeeds via MCP when PRICING_MODE=on and payment provided."""
    config, client = paid_client

    session_id = await negotiate_mcp_session_id(config, client)
    await initialize_mcp_session(config, session_id, client)
    response = await call_mcp_tool(
        config,
        name="search_replies",
        arguments={"conversation_id": "1234567890", "max_items": 5},
        session_id=session_id,
        client=client,
    )
    is_error, _ = parse_mcp_response(response)
    assert not is_error


@pytest.mark.payment_off
async def test_search_replies_missing_conversation_id_returns_422(rest_client) -> None:
    """POST without required 'conversation_id' field returns 422 (only when payment is off)."""
    config, client = rest_client
    response = await client.post(
        "/hybrid/v1/search/replies",
        json={"max_items": 10},
    )
    assert response.status_code == 422

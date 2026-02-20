"""
E2E smoke tests for hybrid endpoints (accessible via both REST and MCP).

Test coverage:
- /api/health (free endpoint)
- /hybrid/v1/search/topic (priced endpoint)
- /hybrid/v1/search/profile (priced endpoint)
- /hybrid/v1/search/profile/latest (priced endpoint)
- /hybrid/v1/search/replies (priced endpoint)
- /hybrid/v1/search/profile/batch (priced endpoint)
- /hybrid/v1/search/profile/latest/batch (priced endpoint)

Payment modes:
- payment_off: Server running with MCP_TWITTER_X402_PRICING_MODE=off
- payment_on: Server running with MCP_TWITTER_X402_PRICING_MODE=on (requires wallet)
"""

from __future__ import annotations

import pytest

from tests.e2e.config import load_e2e_config, require_base_url
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
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.payment_on
async def test_search_topic_rest_no_payment(rest_client) -> None:
    """Priced endpoint returns 402 via REST when PRICING_MODE=on and no payment."""
    config, client = rest_client
    response = await client.post(
        "/hybrid/v1/search/topic",
        json={"topic": "python programming", "max_items": 5},
    )
    assert response.status_code == 402
    body = response.json()
    assert "accepts" in body  # accepts may be empty if no payment schemes configured
    assert body.get("error")


@pytest.mark.payment_on
async def test_search_topic_rest_with_payment(paid_client) -> None:
    """Priced endpoint succeeds via REST when PRICING_MODE=on and payment provided."""
    config, client = paid_client
    response = await client.post(
        "/hybrid/v1/search/topic",
        json={"topic": "python programming", "max_items": 5},
    )
    if response.status_code == 402:
        error_body = response.json()
        pytest.fail(
            f"Payment-enabled test received 402 response. "
            f"Payment flow may not be working correctly. "
            f"Error body: {error_body}"
        )
    response.raise_for_status()
    data = response.json()
    assert isinstance(data, list)


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
    result = extract_mcp_result(response)
    assert not result.get("isError", False)
    result_data = get_mcp_content(result)
    assert isinstance(result_data, list)


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
    body = response.json()
    assert "accepts" in body or "error" in body


@pytest.mark.payment_on
async def test_search_topic_mcp_with_payment(paid_client) -> None:
    """Priced endpoint succeeds via MCP when PRICING_MODE=on and payment provided."""
    config, client = paid_client

    session_id = await negotiate_mcp_session_id_with_client(config, client)
    await initialize_mcp_session_with_client(config, client, session_id)
    response = await call_mcp_tool_with_client(
        config,
        client,
        name="search_topic",
        arguments={"topic": "python programming", "max_items": 5},
        session_id=session_id,
    )
    result = extract_mcp_result(response)
    assert not result.get("isError", False)
    result_data = get_mcp_content(result)
    assert isinstance(result_data, list)


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
# /hybrid/v1/search/profile - Priced endpoint
# =============================================================================


@pytest.mark.payment_off
async def test_search_profile_rest_pricing_off(rest_client) -> None:
    """Priced endpoint works via REST without payment when PRICING_MODE=off."""
    config, client = rest_client
    response = await client.post(
        "/hybrid/v1/search/profile",
        json={"username": "elonmusk", "max_items": 5},
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.payment_on
async def test_search_profile_rest_no_payment(rest_client) -> None:
    """Priced endpoint returns 402 via REST when PRICING_MODE=on and no payment."""
    config, client = rest_client
    response = await client.post(
        "/hybrid/v1/search/profile",
        json={"username": "elonmusk", "max_items": 5},
    )
    assert response.status_code == 402


@pytest.mark.payment_on
async def test_search_profile_rest_with_payment(paid_client) -> None:
    """Priced endpoint succeeds via REST when PRICING_MODE=on and payment provided."""
    config, client = paid_client
    response = await client.post(
        "/hybrid/v1/search/profile",
        json={"username": "elonmusk", "max_items": 5},
    )
    if response.status_code == 402:
        pytest.fail("Payment-enabled test received 402 response.")
    response.raise_for_status()
    data = response.json()
    assert isinstance(data, list)


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
        arguments={"username": "elonmusk", "max_items": 5},
        session_id=session_id,
    )
    result = extract_mcp_result(response)
    assert not result.get("isError", False)
    result_data = get_mcp_content(result)
    assert isinstance(result_data, list)


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
        arguments={"username": "elonmusk", "max_items": 5},
        session_id=session_id,
    )
    assert response.status_code == 402


@pytest.mark.payment_on
async def test_search_profile_mcp_with_payment(paid_client) -> None:
    """Priced endpoint succeeds via MCP when PRICING_MODE=on and payment provided."""
    config, client = paid_client

    session_id = await negotiate_mcp_session_id_with_client(config, client)
    await initialize_mcp_session_with_client(config, client, session_id)
    response = await call_mcp_tool_with_client(
        config,
        client,
        name="search_profile",
        arguments={"username": "elonmusk", "max_items": 5},
        session_id=session_id,
    )
    result = extract_mcp_result(response)
    assert not result.get("isError", False)
    result_data = get_mcp_content(result)
    assert isinstance(result_data, list)


@pytest.mark.payment_off
async def test_search_profile_missing_username_returns_422(rest_client) -> None:
    """POST without required 'username' field returns 422 (only when payment is off)."""
    config, client = rest_client
    response = await client.post(
        "/hybrid/v1/search/profile",
        json={"max_items": 10},
    )
    assert response.status_code == 422


# =============================================================================
# /hybrid/v1/search/profile/latest - Priced endpoint
# =============================================================================


@pytest.mark.payment_off
async def test_search_profile_latest_rest_pricing_off(rest_client) -> None:
    """Priced endpoint works via REST without payment when PRICING_MODE=off."""
    config, client = rest_client
    response = await client.post(
        "/hybrid/v1/search/profile/latest",
        json={"username": "elonmusk", "max_items": 5},
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.payment_on
async def test_search_profile_latest_rest_no_payment(rest_client) -> None:
    """Priced endpoint returns 402 via REST when PRICING_MODE=on and no payment."""
    config, client = rest_client
    response = await client.post(
        "/hybrid/v1/search/profile/latest",
        json={"username": "elonmusk", "max_items": 5},
    )
    assert response.status_code == 402


@pytest.mark.payment_on
async def test_search_profile_latest_rest_with_payment(paid_client) -> None:
    """Priced endpoint succeeds via REST when PRICING_MODE=on and payment provided."""
    config, client = paid_client
    response = await client.post(
        "/hybrid/v1/search/profile/latest",
        json={"username": "elonmusk", "max_items": 5},
    )
    if response.status_code == 402:
        pytest.fail("Payment-enabled test received 402 response.")
    response.raise_for_status()
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.payment_off
async def test_search_profile_latest_mcp_pricing_off() -> None:
    """Priced endpoint works via MCP without payment when PRICING_MODE=off."""
    config = load_e2e_config()
    require_base_url(config)

    session_id = await negotiate_mcp_session_id(config)
    await initialize_mcp_session(config, session_id)
    response = await call_mcp_tool(
        config,
        name="search_profile_latest",
        arguments={"username": "elonmusk", "max_items": 5},
        session_id=session_id,
    )
    result = extract_mcp_result(response)
    assert not result.get("isError", False)
    result_data = get_mcp_content(result)
    assert isinstance(result_data, list)


@pytest.mark.payment_on
async def test_search_profile_latest_mcp_no_payment() -> None:
    """Priced endpoint returns 402 via MCP when PRICING_MODE=on and no payment."""
    config = load_e2e_config()
    require_base_url(config)

    session_id = await negotiate_mcp_session_id(config)
    await initialize_mcp_session(config, session_id)
    response = await call_mcp_tool(
        config,
        name="search_profile_latest",
        arguments={"username": "elonmusk", "max_items": 5},
        session_id=session_id,
    )
    assert response.status_code == 402


@pytest.mark.payment_on
async def test_search_profile_latest_mcp_with_payment(paid_client) -> None:
    """Priced endpoint succeeds via MCP when PRICING_MODE=on and payment provided."""
    config, client = paid_client

    session_id = await negotiate_mcp_session_id_with_client(config, client)
    await initialize_mcp_session_with_client(config, client, session_id)
    response = await call_mcp_tool_with_client(
        config,
        client,
        name="search_profile_latest",
        arguments={"username": "elonmusk", "max_items": 5},
        session_id=session_id,
    )
    result = extract_mcp_result(response)
    assert not result.get("isError", False)
    result_data = get_mcp_content(result)
    assert isinstance(result_data, list)


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
    data = response.json()
    assert isinstance(data, list)


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
    if response.status_code == 402:
        pytest.fail("Payment-enabled test received 402 response.")
    response.raise_for_status()
    data = response.json()
    assert isinstance(data, list)


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
    result = extract_mcp_result(response)
    assert not result.get("isError", False)
    result_data = get_mcp_content(result)
    assert isinstance(result_data, list)


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

    session_id = await negotiate_mcp_session_id_with_client(config, client)
    await initialize_mcp_session_with_client(config, client, session_id)
    response = await call_mcp_tool_with_client(
        config,
        client,
        name="search_replies",
        arguments={"conversation_id": "1234567890", "max_items": 5},
        session_id=session_id,
    )
    result = extract_mcp_result(response)
    assert not result.get("isError", False)
    result_data = get_mcp_content(result)
    assert isinstance(result_data, list)


@pytest.mark.payment_off
async def test_search_replies_missing_conversation_id_returns_422(rest_client) -> None:
    """POST without required 'conversation_id' field returns 422 (only when payment is off)."""
    config, client = rest_client
    response = await client.post(
        "/hybrid/v1/search/replies",
        json={"max_items": 10},
    )
    assert response.status_code == 422


# =============================================================================
# /hybrid/v1/search/profile/batch - Priced endpoint
# =============================================================================


@pytest.mark.payment_off
async def test_search_profile_batch_rest_pricing_off(rest_client) -> None:
    """Priced endpoint works via REST without payment when PRICING_MODE=off."""
    config, client = rest_client
    response = await client.post(
        "/hybrid/v1/search/profile/batch",
        json={"usernames": ["elonmusk", "jack"], "max_items": 3},
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2
    for result in data:
        assert "username" in result
        assert "items" in result


@pytest.mark.payment_on
async def test_search_profile_batch_rest_no_payment(rest_client) -> None:
    """Priced endpoint returns 402 via REST when PRICING_MODE=on and no payment."""
    config, client = rest_client
    response = await client.post(
        "/hybrid/v1/search/profile/batch",
        json={"usernames": ["elonmusk", "jack"], "max_items": 3},
    )
    assert response.status_code == 402


@pytest.mark.payment_on
async def test_search_profile_batch_rest_with_payment(paid_client) -> None:
    """Priced endpoint succeeds via REST when PRICING_MODE=on and payment provided."""
    config, client = paid_client
    response = await client.post(
        "/hybrid/v1/search/profile/batch",
        json={"usernames": ["elonmusk", "jack"], "max_items": 3},
    )
    if response.status_code == 402:
        pytest.fail("Payment-enabled test received 402 response.")
    response.raise_for_status()
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2


@pytest.mark.payment_off
async def test_search_profile_batch_mcp_pricing_off() -> None:
    """Priced endpoint works via MCP without payment when PRICING_MODE=off."""
    config = load_e2e_config()
    require_base_url(config)

    session_id = await negotiate_mcp_session_id(config)
    await initialize_mcp_session(config, session_id)
    response = await call_mcp_tool(
        config,
        name="search_profile_batch",
        arguments={"usernames": ["elonmusk", "jack"], "max_items": 3},
        session_id=session_id,
    )
    result = extract_mcp_result(response)
    assert not result.get("isError", False)
    result_data = get_mcp_content(result)
    assert isinstance(result_data, list)


@pytest.mark.payment_on
async def test_search_profile_batch_mcp_no_payment() -> None:
    """Priced endpoint returns 402 via MCP when PRICING_MODE=on and no payment."""
    config = load_e2e_config()
    require_base_url(config)

    session_id = await negotiate_mcp_session_id(config)
    await initialize_mcp_session(config, session_id)
    response = await call_mcp_tool(
        config,
        name="search_profile_batch",
        arguments={"usernames": ["elonmusk", "jack"], "max_items": 3},
        session_id=session_id,
    )
    assert response.status_code == 402


@pytest.mark.payment_on
async def test_search_profile_batch_mcp_with_payment(paid_client) -> None:
    """Priced endpoint succeeds via MCP when PRICING_MODE=on and payment provided."""
    config, client = paid_client

    session_id = await negotiate_mcp_session_id_with_client(config, client)
    await initialize_mcp_session_with_client(config, client, session_id)
    response = await call_mcp_tool_with_client(
        config,
        client,
        name="search_profile_batch",
        arguments={"usernames": ["elonmusk", "jack"], "max_items": 3},
        session_id=session_id,
    )
    result = extract_mcp_result(response)
    assert not result.get("isError", False)
    result_data = get_mcp_content(result)
    assert isinstance(result_data, list)


@pytest.mark.payment_off
async def test_search_profile_batch_empty_usernames_returns_422(rest_client) -> None:
    """POST with empty usernames list returns 422 (only when payment is off)."""
    config, client = rest_client
    response = await client.post(
        "/hybrid/v1/search/profile/batch",
        json={"usernames": []},
    )
    assert response.status_code == 422


# =============================================================================
# /hybrid/v1/search/profile/latest/batch - Priced endpoint
# =============================================================================


@pytest.mark.payment_off
async def test_search_profile_latest_batch_rest_pricing_off(rest_client) -> None:
    """Priced endpoint works via REST without payment when PRICING_MODE=off."""
    config, client = rest_client
    response = await client.post(
        "/hybrid/v1/search/profile/latest/batch",
        json={"usernames": ["elonmusk", "jack"], "max_items": 3},
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2
    for result in data:
        assert "username" in result
        assert "items" in result


@pytest.mark.payment_on
async def test_search_profile_latest_batch_rest_no_payment(rest_client) -> None:
    """Priced endpoint returns 402 via REST when PRICING_MODE=on and no payment."""
    config, client = rest_client
    response = await client.post(
        "/hybrid/v1/search/profile/latest/batch",
        json={"usernames": ["elonmusk", "jack"], "max_items": 3},
    )
    assert response.status_code == 402


@pytest.mark.payment_on
async def test_search_profile_latest_batch_rest_with_payment(paid_client) -> None:
    """Priced endpoint succeeds via REST when PRICING_MODE=on and payment provided."""
    config, client = paid_client
    response = await client.post(
        "/hybrid/v1/search/profile/latest/batch",
        json={"usernames": ["elonmusk", "jack"], "max_items": 3},
    )
    if response.status_code == 402:
        pytest.fail("Payment-enabled test received 402 response.")
    response.raise_for_status()
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2


@pytest.mark.payment_off
async def test_search_profile_latest_batch_mcp_pricing_off() -> None:
    """Priced endpoint works via MCP without payment when PRICING_MODE=off."""
    config = load_e2e_config()
    require_base_url(config)

    session_id = await negotiate_mcp_session_id(config)
    await initialize_mcp_session(config, session_id)
    response = await call_mcp_tool(
        config,
        name="search_profile_latest_batch",
        arguments={"usernames": ["elonmusk", "jack"], "max_items": 3},
        session_id=session_id,
    )
    result = extract_mcp_result(response)
    assert not result.get("isError", False)
    result_data = get_mcp_content(result)
    assert isinstance(result_data, list)


@pytest.mark.payment_on
async def test_search_profile_latest_batch_mcp_no_payment() -> None:
    """Priced endpoint returns 402 via MCP when PRICING_MODE=on and no payment."""
    config = load_e2e_config()
    require_base_url(config)

    session_id = await negotiate_mcp_session_id(config)
    await initialize_mcp_session(config, session_id)
    response = await call_mcp_tool(
        config,
        name="search_profile_latest_batch",
        arguments={"usernames": ["elonmusk", "jack"], "max_items": 3},
        session_id=session_id,
    )
    assert response.status_code == 402


@pytest.mark.payment_on
async def test_search_profile_latest_batch_mcp_with_payment(paid_client) -> None:
    """Priced endpoint succeeds via MCP when PRICING_MODE=on and payment provided."""
    config, client = paid_client

    session_id = await negotiate_mcp_session_id_with_client(config, client)
    await initialize_mcp_session_with_client(config, client, session_id)
    response = await call_mcp_tool_with_client(
        config,
        client,
        name="search_profile_latest_batch",
        arguments={"usernames": ["elonmusk", "jack"], "max_items": 3},
        session_id=session_id,
    )
    result = extract_mcp_result(response)
    assert not result.get("isError", False)
    result_data = get_mcp_content(result)
    assert isinstance(result_data, list)

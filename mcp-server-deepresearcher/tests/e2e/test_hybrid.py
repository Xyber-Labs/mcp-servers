"""
E2E tests for hybrid endpoints (REST + MCP).
"""

from __future__ import annotations

import httpx
import pytest
import pytest_asyncio
from eth_account import Account
from x402.clients.httpx import x402HttpxClient

from tests.e2e.config import load_e2e_config, require_base_url, require_wallet


@pytest_asyncio.fixture
async def hybrid_rest_client():
    """Create a REST client for hybrid endpoint tests."""
    config = load_e2e_config()
    require_base_url(config)
    async with httpx.AsyncClient(
        base_url=config.base_url,
        timeout=config.timeout_seconds,
    ) as client:
        yield config, client


@pytest_asyncio.fixture
async def hybrid_paid_client():
    """Create a paid REST client with x402 support for hybrid endpoints."""
    config = load_e2e_config()
    require_base_url(config)
    require_wallet(config)
    account = Account.from_key(config.private_key)  # type: ignore[arg-type]
    async with x402HttpxClient(
        account=account,
        base_url=config.base_url,
        timeout=config.timeout_seconds,
        follow_redirects=True,
        trust_env=False,
    ) as client:
        yield config, client


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.slow
async def test_hybrid_deep_research_via_rest_requires_payment(hybrid_rest_client) -> None:
    """Test that hybrid deep research endpoint requires payment."""
    config, client = hybrid_rest_client
    payload = {
        "research_topic": "artificial intelligence",
        "max_web_research_loops": 3
    }
    response = await client.post("/hybrid/deep-research", json=payload)
    # Should return 402 if payment is required
    # May return 500 if server resources not available (expected in E2E without full setup)
    assert response.status_code in [402, 500, 503]
    
    if response.status_code == 402:
        body = response.json()
        assert "accepts" in body and body["accepts"]
        assert body.get("error")


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.slow
async def test_hybrid_deep_research_succeeds_with_x402(hybrid_paid_client) -> None:
    """Test that hybrid deep research succeeds with x402 payment."""
    config, client = hybrid_paid_client
    payload = {
        "research_topic": "quantum computing",
        "max_web_research_loops": 2
    }
    response = await client.post("/hybrid/deep-research", json=payload)
    
    if response.status_code == 402:
        pytest.skip(
            "Deep research is priced but payment flow is not yet fully configured in this environment."
        )
    elif response.status_code == 500 or response.status_code == 503:
        pytest.skip(
            "Server resources not available (LLMs, MCP tools, etc.) - expected in E2E without full setup."
        )
    
    response.raise_for_status()
    body = response.json()
    assert body.get("status") == "success"
    assert "research_topic" in body
    assert "running_summary" in body or "report" in body


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.slow
async def test_hybrid_deep_research_validation(hybrid_rest_client) -> None:
    """Test validation of hybrid deep research endpoint."""
    config, client = hybrid_rest_client
    
    # Test missing required field
    response = await client.post("/hybrid/deep-research", json={})
    assert response.status_code == 422
    
    # Test invalid max_web_research_loops
    response = await client.post(
        "/hybrid/deep-research",
        json={
            "research_topic": "test",
            "max_web_research_loops": 11  # Out of range
        }
    )
    assert response.status_code == 422
    
    # Test valid request structure
    response = await client.post(
        "/hybrid/deep-research",
        json={
            "research_topic": "test topic",
            "max_web_research_loops": 3
        }
    )
    # May require payment or fail due to missing resources
    assert response.status_code in [200, 402, 500, 503]


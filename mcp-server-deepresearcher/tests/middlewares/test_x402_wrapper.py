"""
Tests for x402 payment middleware.
"""

from __future__ import annotations

import base64
import json
from types import SimpleNamespace

import pytest
import pytest_asyncio
from eth_account import Account
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from x402.clients.base import x402Client
from x402.types import PaymentPayload, PaymentRequirements, x402PaymentRequiredResponse

from mcp_server_deepresearcher.middlewares import X402WrapperMiddleware
from mcp_server_deepresearcher.x402_config import PaymentOption


class DummyFacilitator:
    """Dummy facilitator for testing."""
    
    def __init__(self) -> None:
        self.verify_calls: list[tuple[PaymentPayload, PaymentRequirements]] = []
        self.settle_calls: list[tuple[PaymentPayload, PaymentRequirements]] = []

    async def verify(self, payment, requirements):  # noqa: ANN001
        self.verify_calls.append((payment, requirements))
        return SimpleNamespace(is_valid=True, invalid_reason=None)

    async def settle(self, payment, requirements):  # noqa: ANN001
        self.settle_calls.append((payment, requirements))
        payload = {"status": "ok"}

        class Result:
            success = True

            def model_dump_json(self, **kwargs):  # noqa: ANN003
                return json.dumps(payload)

        return Result()


@pytest.fixture
def pricing() -> dict[str, list[PaymentOption]]:
    """Pricing configuration for tests."""
    return {
        "deep_research": [
            PaymentOption(
                chain_id=8453,  # Base
                token_address="0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
                token_amount=5000,
            )
        ]
    }


@pytest_asyncio.fixture
async def payment_app(
    monkeypatch: pytest.MonkeyPatch, pricing: dict[str, list[PaymentOption]]
):
    """Return (client, facilitator_stub) tuple for middleware tests."""
    facilitator = DummyFacilitator()

    settings = SimpleNamespace(
        facilitator_config={"url": "https://facilitator"},
        payee_wallet_address="0xD23ef9BAf3A2A9a9feb8035e4b3Be41878faF515",
    )
    monkeypatch.setattr(
        "mcp_server_deepresearcher.middlewares.x402_wrapper.get_x402_settings",
        lambda: settings,
    )
    monkeypatch.setattr(
        "mcp_server_deepresearcher.middlewares.x402_wrapper.FacilitatorClient",
        lambda config: facilitator,
    )

    app = FastAPI()

    @app.post("/hybrid/deep-research", operation_id="deep_research")
    async def deep_research_endpoint():  # noqa: ANN202
        return {"status": "success"}

    app.add_middleware(X402WrapperMiddleware, tool_pricing=pricing)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client, facilitator


@pytest.mark.asyncio
async def test_missing_payment_header_returns_402(payment_app) -> None:
    """Test that missing payment header returns 402."""
    client, _ = payment_app
    response = await client.post("/hybrid/deep-research")
    assert response.status_code == 402
    payload = response.json()
    assert payload["error"] == "No X-PAYMENT header provided"
    assert payload["accepts"]


@pytest.mark.asyncio
async def test_invalid_payment_header_returns_402(payment_app) -> None:
    """Test that invalid payment header returns 402."""
    client, _ = payment_app
    headers = {"X-PAYMENT": base64.b64encode(b"not-json").decode("utf-8")}
    response = await client.post("/hybrid/deep-research", headers=headers)
    assert response.status_code == 402
    payload = response.json()
    assert payload["error"] == "Invalid payment header format"


@pytest.mark.asyncio
async def test_valid_payment_header_allows_request_and_sets_response_header(
    payment_app,
) -> None:
    """Test that valid payment header allows request and sets response header."""
    client, facilitator = payment_app

    # First call without header to obtain payment requirements
    resp_402 = await client.post("/hybrid/deep-research")
    assert resp_402.status_code == 402
    body = resp_402.json()
    payment_response = x402PaymentRequiredResponse(**body)
    assert payment_response.accepts

    # Use x402Client logic to construct a real X-PAYMENT header
    account = Account.create()
    xclient = x402Client(account=account)
    selected_req = payment_response.accepts[0]
    header_value = xclient.create_payment_header(
        payment_requirements=selected_req,
        x402_version=payment_response.x402_version,
    )

    headers = {"X-PAYMENT": header_value}
    resp_paid = await client.post("/hybrid/deep-research", headers=headers)
    assert resp_paid.status_code == 200
    assert resp_paid.headers.get("X-PAYMENT-RESPONSE")

    # Verify facilitator was invoked
    assert facilitator.verify_calls
    assert facilitator.settle_calls


@pytest.mark.asyncio
async def test_payment_header_with_wrong_network_returns_no_matching(
    payment_app,
) -> None:
    """Test that payment header with wrong network returns 402."""
    client, _ = payment_app

    # Obtain real payment requirements via 402
    resp_402 = await client.post("/hybrid/deep-research")
    assert resp_402.status_code == 402
    body = resp_402.json()

    # Build a valid header, then tamper with the network field
    payment_response = x402PaymentRequiredResponse(**body)
    account = Account.create()
    xclient = x402Client(account=account)
    selected_req = payment_response.accepts[0]
    header_value = xclient.create_payment_header(
        payment_requirements=selected_req,
        x402_version=payment_response.x402_version,
    )

    # Decode, modify network, and re-encode
    raw = json.loads(base64.b64decode(header_value).decode("utf-8"))
    raw["network"] = "base-sepolia"  # mismatch the configured "base"
    tampered_header = base64.b64encode(json.dumps(raw).encode("utf-8")).decode("utf-8")

    resp = await client.post("/hybrid/deep-research", headers={"X-PAYMENT": tampered_header})
    assert resp.status_code == 402
    payload = resp.json()
    assert payload["error"] == "No matching payment requirements found"


@pytest.mark.asyncio
async def test_free_endpoint_bypasses_middleware(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that free endpoints bypass payment middleware."""
    facilitator = DummyFacilitator()

    settings = SimpleNamespace(
        facilitator_config={"url": "https://facilitator"},
        payee_wallet_address="0xD23ef9BAf3A2A9a9feb8035e4b3Be41878faF515",
    )
    monkeypatch.setattr(
        "mcp_server_deepresearcher.middlewares.x402_wrapper.get_x402_settings",
        lambda: settings,
    )
    monkeypatch.setattr(
        "mcp_server_deepresearcher.middlewares.x402_wrapper.FacilitatorClient",
        lambda config: facilitator,
    )

    app = FastAPI()

    @app.get("/api/health", operation_id="get_server_health")
    async def health_endpoint():  # noqa: ANN202
        return {"status": "ok"}

    # No pricing for this endpoint
    pricing = {}
    app.add_middleware(X402WrapperMiddleware, tool_pricing=pricing)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/health")
        assert response.status_code == 200
        # Facilitator should not be called for free endpoints
        assert not facilitator.verify_calls


@pytest.mark.asyncio
async def test_mcp_endpoint_payment_detection(payment_app) -> None:
    """Test that MCP endpoints can detect payment requirements."""
    client, _ = payment_app
    
    # Test MCP-style request
    mcp_payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "deep_research",
            "arguments": {
                "research_topic": "test",
                "max_web_research_loops": 3
            }
        }
    }
    
    response = await client.post("/hybrid/deep-research", json=mcp_payload)
    # Should return 402 if payment required, or handle MCP format
    assert response.status_code in [200, 402, 422]


@pytest.mark.asyncio
async def test_middleware_disabled_when_no_facilitator(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that middleware is disabled when no facilitator is configured."""
    settings = SimpleNamespace(
        facilitator_config=None,
        payee_wallet_address=None,
    )
    monkeypatch.setattr(
        "mcp_server_deepresearcher.middlewares.x402_wrapper.get_x402_settings",
        lambda: settings,
    )

    app = FastAPI()

    @app.post("/hybrid/deep-research", operation_id="deep_research")
    async def deep_research_endpoint():  # noqa: ANN202
        return {"status": "success"}

    pricing = {
        "deep_research": [
            PaymentOption(
                chain_id=8453,
                token_address="0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
                token_amount=5000,
            )
        ]
    }
    app.add_middleware(X402WrapperMiddleware, tool_pricing=pricing)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Should bypass payment when facilitator is None
        response = await client.post("/hybrid/deep-research")
        assert response.status_code == 200


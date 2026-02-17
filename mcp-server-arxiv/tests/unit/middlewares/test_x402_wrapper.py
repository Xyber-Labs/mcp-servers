from __future__ import annotations

import base64
import json
from types import SimpleNamespace

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from mcp_server_arxiv.middlewares import X402WrapperMiddleware
from mcp_server_arxiv.x402_integration import PaymentOptionConfig


class DummyFacilitator:
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
def pricing() -> dict[str, list[PaymentOptionConfig]]:
    return {
        "arxiv_search": [
            PaymentOptionConfig(
                chain_id=8453,  # Base Mainnet
                token_address="0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
                price_usd=0.01,
            )
        ]
    }


@pytest_asyncio.fixture
async def payment_app(
    monkeypatch: pytest.MonkeyPatch, pricing: dict[str, list[PaymentOptionConfig]]
):
    """Return (client, facilitator_stub, server_stub) tuple for middleware tests."""

    facilitator = DummyFacilitator()

    # Mock server with required methods
    class DummyServer:
        def __init__(self):
            self._schemes = {}
            self._supported_responses = {}

        def initialize(self):
            pass

        def register(self, network, scheme):
            pass

        async def verify_payment(self, payment, requirements):
            return SimpleNamespace(is_valid=True, invalid_reason=None)

        async def settle_payment(self, payment, requirements):
            payload = {"status": "ok"}
            class Result:
                success = True
                def model_dump_json(self, **kwargs):
                    return json.dumps(payload)
            return Result()

    server = DummyServer()

    settings = SimpleNamespace(
        facilitator_config=SimpleNamespace(url="https://facilitator", auth_provider=None),
        payee_evm_address="0xD23ef9BAf3A2A9a9feb8035e4b3Be41878faF515",
        payee_solana_address=None,
    )

    def mock_get_payee_address(network):
        if "solana" in str(network):
            return settings.payee_solana_address
        return settings.payee_evm_address

    settings.get_payee_address = mock_get_payee_address

    monkeypatch.setattr(
        "mcp_server_arxiv.middlewares.x402_wrapper.get_x402_settings",
        lambda: settings,
    )
    monkeypatch.setattr(
        "mcp_server_arxiv.middlewares.x402_wrapper.HTTPFacilitatorClient",
        lambda config: facilitator,
    )
    monkeypatch.setattr(
        "mcp_server_arxiv.middlewares.x402_wrapper.x402ResourceServer",
        lambda facilitator: server,
    )

    app = FastAPI()

    @app.post("/hybrid/search", operation_id="arxiv_search")
    async def search_endpoint():  # noqa: ANN202
        return {"ok": True}

    app.add_middleware(X402WrapperMiddleware, tool_pricing=pricing)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client, facilitator, server


@pytest.mark.asyncio
async def test_missing_payment_header_returns_402(payment_app) -> None:
    client, _, _ = payment_app
    response = await client.post("/hybrid/search")
    assert response.status_code == 402
    payload = response.json()
    assert payload["error"] == "No payment header provided"
    assert payload["accepts"]


@pytest.mark.asyncio
async def test_invalid_payment_header_returns_402(payment_app) -> None:
    client, _, _ = payment_app
    headers = {"PAYMENT-SIGNATURE": base64.b64encode(b"not-json").decode("utf-8")}
    response = await client.post("/hybrid/search", headers=headers)
    assert response.status_code == 402
    payload = response.json()
    assert payload["error"] == "Invalid payment header format"


@pytest.mark.asyncio
@pytest.mark.skip(reason="TODO: Update for x402 v2.0.0 - x402Client API has changed")
async def test_valid_payment_header_allows_request_and_sets_response_header(
    payment_app,
) -> None:
    """
    NOTE: This test needs to be updated for x402 v2.0.0
    The x402Client API and payment flow has changed significantly in v2.
    """
    client, facilitator, server = payment_app

    # First call without header to obtain payment requirements
    resp_402 = await client.post("/hybrid/search")
    assert resp_402.status_code == 402
    body = resp_402.json()
    # TODO: Update for v2 PaymentRequired format
    # payment_response = PaymentRequired(**body)
    # assert payment_response.accepts

    # TODO: Use x402 v2 client to construct payment header
    # The API has changed significantly in v2


@pytest.mark.asyncio
@pytest.mark.skip(reason="TODO: Update for x402 v2.0.0 - x402Client API has changed")
async def test_payment_header_with_wrong_network_returns_no_matching(
    payment_app,
) -> None:
    """
    NOTE: This test needs to be updated for x402 v2.0.0
    The x402Client API and payment flow has changed significantly in v2.
    """
    client, _, _ = payment_app

    # TODO: Update for v2 PaymentRequired format and client API

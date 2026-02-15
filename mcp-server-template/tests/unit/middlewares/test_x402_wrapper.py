from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
import pytest_asyncio
from eth_account import Account
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from x402.http import safe_base64_encode

from mcp_server_weather.middlewares import X402WrapperMiddleware
from mcp_server_weather.x402_integration.config import PaymentOptionConfig


class DummyServer:
    """Mock x402ResourceServer for testing."""

    def __init__(self) -> None:
        self.verify_calls: list[tuple] = []
        self.settle_calls: list[tuple] = []
        self._schemes: dict = {}  # Mock internal schemes registry
        self._supported_responses: dict = {}  # Mock supported responses

    def initialize(self) -> None:
        """Mock initialize - does nothing in tests."""
        pass

    def register(self, network: str, scheme) -> None:  # noqa: ANN001
        pass

    async def verify_payment(self, payment, requirements):  # noqa: ANN001
        self.verify_calls.append((payment, requirements))
        return SimpleNamespace(is_valid=True, invalid_reason=None)

    async def settle_payment(self, payment, requirements):  # noqa: ANN001
        self.settle_calls.append((payment, requirements))
        payload = {"status": "ok"}

        class Result:
            success = True
            error_reason = None

            def model_dump_json(self, **kwargs):  # noqa: ANN003
                return json.dumps(payload)

        return Result()


@pytest.fixture
def pricing() -> dict[str, list[PaymentOptionConfig]]:
    return {
        "get_weather_forecast": [
            PaymentOptionConfig(
                chain_id=84532,  # Base Sepolia - supported by public facilitator
                token_address="0x036CbD53842c5426634e7929541eC2318f3dCF7e",  # USDC on Base Sepolia
                price_usd=0.001,  # $0.001 = 1000 token units with 6 decimals
            )
        ]
    }


@pytest_asyncio.fixture
async def payment_app(
    monkeypatch: pytest.MonkeyPatch, pricing: dict[str, list[PaymentOptionConfig]]
):
    """Return (client, server_stub) tuple for middleware tests."""

    dummy_server = DummyServer()

    # Mock facilitator config (must be a list)
    mock_facilitator = SimpleNamespace(url="https://facilitator")
    settings = SimpleNamespace(
        facilitator_config=[mock_facilitator],
        get_payee_address=lambda network: "0xD23ef9BAf3A2A9a9feb8035e4b3Be41878faF515",
    )
    monkeypatch.setattr(
        "mcp_server_weather.middlewares.x402_wrapper.get_x402_settings",
        lambda: settings,
    )
    # Mock HTTPFacilitatorClient to return object with _url attribute
    monkeypatch.setattr(
        "mcp_server_weather.middlewares.x402_wrapper.HTTPFacilitatorClient",
        lambda config: SimpleNamespace(_url=config.url),
    )
    monkeypatch.setattr(
        "mcp_server_weather.middlewares.x402_wrapper.x402ResourceServer",
        lambda facilitator: dummy_server,
    )

    app = FastAPI()

    @app.post("/hybrid/forecast", operation_id="get_weather_forecast")
    async def forecast_endpoint():  # noqa: ANN202
        return {"ok": True}

    app.add_middleware(X402WrapperMiddleware, tool_pricing=pricing)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client, dummy_server


@pytest.mark.asyncio
async def test_missing_payment_header_returns_402(payment_app) -> None:
    client, _ = payment_app
    response = await client.post("/hybrid/forecast")
    assert response.status_code == 402
    payload = response.json()
    assert payload["error"] == "No payment header provided"
    assert payload["accepts"]
    assert payload["x402Version"] == 2


@pytest.mark.asyncio
async def test_invalid_payment_header_returns_402(payment_app) -> None:
    client, _ = payment_app
    headers = {"PAYMENT-SIGNATURE": safe_base64_encode("not-json")}
    response = await client.post("/hybrid/forecast", headers=headers)
    assert response.status_code == 402
    payload = response.json()
    assert payload["error"] == "Invalid payment header format"


@pytest.mark.asyncio
async def test_valid_payment_header_allows_request_and_sets_response_header(
    payment_app,
) -> None:
    client, server = payment_app

    # First call without header to obtain payment requirements
    resp_402 = await client.post("/hybrid/forecast")
    assert resp_402.status_code == 402
    body = resp_402.json()
    assert body["accepts"]
    assert body["x402Version"] == 2

    # Create a mock v2 payment payload that matches the requirements
    account = Account.create()
    # v2 PaymentPayload structure
    payment_payload = {
        "x402Version": 2,
        "payload": {
            "signature": "0x" + "00" * 65,
            "authorization": {
                "from": account.address,
                "to": "0xD23ef9BAf3A2A9a9feb8035e4b3Be41878faF515",
                "value": "1000",
                "validAfter": 0,
                "validBefore": 9999999999,
                "nonce": "0x" + "00" * 32,
            },
        },
        "accepted": {
            "scheme": "exact",
            "network": "eip155:84532",  # Base Sepolia
            "asset": "0x036CbD53842c5426634e7929541eC2318f3dCF7e",  # USDC on Base Sepolia
            "amount": "1000",
            "payTo": "0xD23ef9BAf3A2A9a9feb8035e4b3Be41878faF515",
            "maxTimeoutSeconds": 60,
        },
    }
    header_value = safe_base64_encode(json.dumps(payment_payload))

    headers = {"PAYMENT-SIGNATURE": header_value}
    resp_paid = await client.post("/hybrid/forecast", headers=headers)
    assert resp_paid.status_code == 200
    assert resp_paid.headers.get("PAYMENT-RESPONSE")

    # Verify server was invoked
    assert server.verify_calls
    assert server.settle_calls


@pytest.mark.asyncio
async def test_legacy_x_payment_header_also_works(payment_app) -> None:
    """Test backward compatibility with X-PAYMENT header."""
    client, server = payment_app

    # Create a mock v2 payment payload
    account = Account.create()
    payment_payload = {
        "x402Version": 2,
        "payload": {
            "signature": "0x" + "00" * 65,
            "authorization": {
                "from": account.address,
                "to": "0xD23ef9BAf3A2A9a9feb8035e4b3Be41878faF515",
                "value": "1000",
                "validAfter": 0,
                "validBefore": 9999999999,
                "nonce": "0x" + "00" * 32,
            },
        },
        "accepted": {
            "scheme": "exact",
            "network": "eip155:84532",  # Base Sepolia
            "asset": "0x036CbD53842c5426634e7929541eC2318f3dCF7e",  # USDC on Base Sepolia
            "amount": "1000",
            "payTo": "0xD23ef9BAf3A2A9a9feb8035e4b3Be41878faF515",
            "maxTimeoutSeconds": 60,
        },
    }
    header_value = safe_base64_encode(json.dumps(payment_payload))

    # Use legacy header
    headers = {"X-PAYMENT": header_value}
    resp_paid = await client.post("/hybrid/forecast", headers=headers)
    assert resp_paid.status_code == 200


@pytest.mark.asyncio
async def test_payment_header_with_wrong_network_returns_no_matching(
    payment_app,
) -> None:
    client, _ = payment_app

    # Create a v2 payment payload with wrong network
    account = Account.create()
    payment_payload = {
        "x402Version": 2,
        "payload": {
            "signature": "0x" + "00" * 65,
            "authorization": {
                "from": account.address,
                "to": "0xD23ef9BAf3A2A9a9feb8035e4b3Be41878faF515",
                "value": "1000",
                "validAfter": 0,
                "validBefore": 9999999999,
                "nonce": "0x" + "00" * 32,
            },
        },
        "accepted": {
            "scheme": "exact",
            "network": "eip155:8453",  # Wrong network (mainnet instead of sepolia)
            "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
            "amount": "1000",
            "payTo": "0xD23ef9BAf3A2A9a9feb8035e4b3Be41878faF515",
            "maxTimeoutSeconds": 60,
        },
    }
    header_value = safe_base64_encode(json.dumps(payment_payload))

    resp = await client.post(
        "/hybrid/forecast", headers={"PAYMENT-SIGNATURE": header_value}
    )
    assert resp.status_code == 402
    payload = resp.json()
    assert payload["error"] == "No matching payment requirements found"

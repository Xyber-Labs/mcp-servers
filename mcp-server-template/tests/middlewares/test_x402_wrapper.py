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

from mcp_server_weather.config import PaymentOption
from mcp_server_weather.middlewares import X402WrapperMiddleware


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
def pricing() -> dict[str, list[PaymentOption]]:
    return {
        "get_weather_forecast": [
            PaymentOption(
                chain_id=8453,
                token_address="0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
                token_amount=1000,
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
        "mcp_server_weather.middlewares.x402_wrapper.get_x402_settings",
        lambda: settings,
    )
    monkeypatch.setattr(
        "mcp_server_weather.middlewares.x402_wrapper.FacilitatorClient",
        lambda config: facilitator,
    )

    app = FastAPI()

    @app.post("/hybrid/forecast", operation_id="get_weather_forecast")
    async def forecast_endpoint():  # noqa: ANN202
        return {"ok": True}

    app.add_middleware(X402WrapperMiddleware, tool_pricing=pricing)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client, facilitator


@pytest.mark.asyncio
async def test_missing_payment_header_returns_402(payment_app) -> None:
    client, _ = payment_app
    response = await client.post("/hybrid/forecast")
    assert response.status_code == 402
    payload = response.json()
    assert payload["error"] == "No X-PAYMENT header provided"
    assert payload["accepts"]


@pytest.mark.asyncio
async def test_invalid_payment_header_returns_402(payment_app) -> None:
    client, _ = payment_app
    headers = {"X-PAYMENT": base64.b64encode(b"not-json").decode("utf-8")}
    response = await client.post("/hybrid/forecast", headers=headers)
    assert response.status_code == 402
    payload = response.json()
    assert payload["error"] == "Invalid payment header format"


@pytest.mark.asyncio
async def test_valid_payment_header_allows_request_and_sets_response_header(
    payment_app,
) -> None:
    client, facilitator = payment_app

    # First call without header to obtain payment requirements
    resp_402 = await client.post("/hybrid/forecast")
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
    resp_paid = await client.post("/hybrid/forecast", headers=headers)
    assert resp_paid.status_code == 200
    assert resp_paid.headers.get("X-PAYMENT-RESPONSE")

    # Verify facilitator was invoked
    assert facilitator.verify_calls
    assert facilitator.settle_calls


@pytest.mark.asyncio
async def test_payment_header_with_wrong_network_returns_no_matching(
    payment_app,
) -> None:
    client, _ = payment_app

    # Obtain real payment requirements via 402
    resp_402 = await client.post("/hybrid/forecast")
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

    resp = await client.post("/hybrid/forecast", headers={"X-PAYMENT": tampered_header})
    assert resp.status_code == 402
    payload = resp.json()
    assert payload["error"] == "No matching payment requirements found"

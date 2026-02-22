from __future__ import annotations

import base64
import json

import httpx
import pytest_asyncio
from config import load_e2e_config, require_base_url, require_wallet
from eth_account import Account
from x402.client import x402Client
from x402.http.clients import x402HttpxClient
from x402.mechanisms.evm.exact import register_exact_evm_client
from x402.mechanisms.evm.signers import EthAccountSigner
from x402.mechanisms.evm.utils import NETWORK_CONFIGS

# Register SKALE Base network (not yet in x402 library)
if "eip155:1187947933" not in NETWORK_CONFIGS:
    NETWORK_CONFIGS["eip155:1187947933"] = {
        "chain_id": 1187947933,
        "default_asset": {
            "address": "0x85889c8c714505E0c94b30fcfcF64fE3Ac8FCb20",
            "name": "Bridged USDC (SKALE Bridge)",  # Must match Kobaru's expected name
            "version": "2",
            "decimals": 6,
        },
        "supported_assets": {
            "USDC": {
                "address": "0x85889c8c714505E0c94b30fcfcF64fE3Ac8FCb20",
                "name": "Bridged USDC (SKALE Bridge)",  # Must match Kobaru's expected name
                "version": "2",
                "decimals": 6,
            },
            "USDT": {
                "address": "0x2bF5bF154b515EaA82C31a65ec11554fF5aF7fCA",
                "name": "Tether USD",
                "version": "1",
                "decimals": 6,
            },
        },
    }


def print_payment_info(response):
    """Print decoded payment info from response headers."""
    if "payment-response" in response.headers:
        data = json.loads(base64.b64decode(response.headers["payment-response"]))
        print(f"\n[Payment] tx={data.get('transaction')} network={data.get('network')}")


@pytest_asyncio.fixture
async def rest_client():
    """Fixture providing a standard HTTP client for e2e tests."""
    config = load_e2e_config()
    require_base_url(config)
    async with httpx.AsyncClient(
        base_url=config.base_url,
        timeout=config.timeout_seconds,
    ) as client:
        yield config, client


@pytest_asyncio.fixture
async def paid_client():
    """Fixture providing an x402-enabled HTTP client for paid e2e tests.

    Uses x402HttpxClient which automatically handles 402 responses and
    payment signing for EVM networks.
    """
    config = load_e2e_config()
    require_base_url(config)
    require_wallet(config)

    # Create eth account from private key
    account = Account.from_key(config.private_key)  # type: ignore[arg-type]
    signer = EthAccountSigner(account)

    # Create x402 client and register EVM scheme
    x402_client = x402Client()
    register_exact_evm_client(x402_client, signer)

    # Create x402HttpxClient which handles payments automatically
    async with x402HttpxClient(
        x402_client,
        base_url=config.base_url,
        timeout=config.timeout_seconds,
        follow_redirects=True,
        trust_env=False,
    ) as client:
        wrapper = PaymentTrackingClient(client)
        yield config, wrapper


class PaymentTrackingClient:
    """Wrapper that tracks payment responses from x402HttpxClient."""

    def __init__(self, client: x402HttpxClient):
        self._client = client
        self.last_payment_response = None

    async def _track_payment(self, response):
        if "payment-response" in response.headers:
            self.last_payment_response = response.headers["payment-response"]
            print_payment_info(response)
        return response

    async def get(self, *args, **kwargs):
        response = await self._client.get(*args, **kwargs)
        return await self._track_payment(response)

    async def post(self, *args, **kwargs):
        response = await self._client.post(*args, **kwargs)
        return await self._track_payment(response)

    async def put(self, *args, **kwargs):
        response = await self._client.put(*args, **kwargs)
        return await self._track_payment(response)

    async def delete(self, *args, **kwargs):
        response = await self._client.delete(*args, **kwargs)
        return await self._track_payment(response)

    async def patch(self, *args, **kwargs):
        response = await self._client.patch(*args, **kwargs)
        return await self._track_payment(response)

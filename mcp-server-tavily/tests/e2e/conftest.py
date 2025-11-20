from __future__ import annotations

import httpx
import pytest_asyncio
from eth_account import Account
from x402.clients.httpx import x402HttpxClient

from tests.e2e.config import load_e2e_config, require_base_url, require_wallet


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
    """Fixture providing an x402-enabled HTTP client for paid e2e tests."""
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


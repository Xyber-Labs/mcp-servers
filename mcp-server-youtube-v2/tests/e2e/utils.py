"""Utility functions for e2e tests."""

import httpx


async def assert_payment_required(response: httpx.Response):
    """Assert that a response is a 402 Payment Required with proper headers."""
    assert response.status_code == 402
    assert "payment-required" in response.headers or "x-payment-required" in response.headers
    data = response.json()
    assert "accepts" in data
    assert isinstance(data["accepts"], list)
    assert len(data["accepts"]) > 0


async def assert_successful_payment(response: httpx.Response):
    """Assert that a response includes a successful payment receipt."""
    assert response.status_code == 200
    assert "payment-response" in response.headers or "x-payment-response" in response.headers

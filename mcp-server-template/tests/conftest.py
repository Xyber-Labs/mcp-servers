from __future__ import annotations

import asyncio
import os
from collections.abc import Iterator

import pytest


@pytest.fixture(scope="session", autouse=True)
def _ensure_weather_api_key() -> None:
    """Guarantee WEATHER_API_KEY is available for config validation."""

    os.environ.setdefault(
        "WEATHER_API_KEY", os.getenv("WEATHER_API_KEY", "test-api-key")
    )


@pytest.fixture(scope="session")
def event_loop() -> Iterator[asyncio.AbstractEventLoop]:
    """Create an event loop for async tests scoped to the session."""

    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

from __future__ import annotations

import asyncio
from collections.abc import Iterator

import pytest


@pytest.fixture(scope="session")
def event_loop() -> Iterator[asyncio.AbstractEventLoop]:
    """Create an event loop for async tests scoped to the session."""

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        yield loop
    finally:
        loop.close()

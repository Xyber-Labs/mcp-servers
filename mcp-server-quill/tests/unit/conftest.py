from __future__ import annotations

from unittest.mock import patch

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from mcp_server_quill.app import create_app
from mcp_server_quill.x402_integration import X402Config


@pytest_asyncio.fixture
async def client() -> AsyncClient:
    """Create an authenticated AsyncClient for the app.

    We force pricing_mode to 'off' to ensure tests run without payment requirements.
    """
    with patch("mcp_server_quill.app.get_x402_settings") as mock_get_settings:
        real_config = X402Config()
        test_config = real_config.model_copy(update={"pricing_mode": "off"})
        mock_get_settings.return_value = test_config

        app = create_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c

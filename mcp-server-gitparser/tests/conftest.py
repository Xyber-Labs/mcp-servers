import os

import pytest


@pytest.fixture(autouse=True)
def _isolate_docs_dir(tmp_path, monkeypatch):
    """
    Force the server to write docs into a temp directory during tests.
    Also clears cached settings between tests.
    """
    monkeypatch.setenv("MCP_GITPARSER_DOCS_DIR", str(tmp_path / "docs"))

    from mcp_server_gitparser.config import get_app_settings

    get_app_settings.cache_clear()
    yield
    get_app_settings.cache_clear()


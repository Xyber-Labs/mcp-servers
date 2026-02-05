from starlette.routing import Mount


def test_api_routers_only_health():
    from mcp_server_gitparser.api_routers import routers

    assert len(routers) == 1
    assert any(r.path == "/health" for r in routers[0].routes)


def test_app_mounts_expected_routes():
    from mcp_server_gitparser.app import create_app

    app = create_app()
    paths = {getattr(r, "path", None) for r in app.routes}

    assert "/api/health" in paths
    assert "/hybrid/parse-gitbook" in paths
    assert "/hybrid/parse-github" in paths

    # No legacy, unprefixed endpoints
    assert "/parse-gitbook" not in paths
    assert "/parse-github" not in paths

    # MCP is mounted as a sub-app
    assert any(isinstance(r, Mount) and r.path == "/mcp" for r in app.routes)


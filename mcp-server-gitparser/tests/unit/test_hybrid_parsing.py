from fastapi.testclient import TestClient


def test_hybrid_parse_gitbook_writes_file(monkeypatch):
    from mcp_server_gitparser.app import create_app

    async def _fake_convert_gitbook_to_markdown(_url: str) -> str:
        return "# hello from gitbook\n"

    # Patch where it's imported/used
    monkeypatch.setattr(
        "mcp_server_gitparser.hybrid_routers.parsing.convert_gitbook_to_markdown",
        _fake_convert_gitbook_to_markdown,
    )

    app = create_app()
    client = TestClient(app)

    resp = client.post("/hybrid/parse-gitbook", json={"url": "https://docs.gitbook.com"})
    assert resp.status_code == 200
    data = resp.json()

    assert data["success"] is True
    assert data["markdown"].startswith("# hello from gitbook")
    assert data["length"] > 0
    assert data["file_path"].endswith(".md")

    # File should exist
    from pathlib import Path

    assert Path(data["file_path"]).exists()


def test_hybrid_parse_github_writes_file(monkeypatch):
    from mcp_server_gitparser.app import create_app

    async def _fake_convert_repo_to_markdown(*_args, **_kwargs) -> str:
        return "# repo digest\n"

    monkeypatch.setattr(
        "mcp_server_gitparser.hybrid_routers.parsing.convert_repo_to_markdown",
        _fake_convert_repo_to_markdown,
    )

    app = create_app()
    client = TestClient(app)

    resp = client.post(
        "/hybrid/parse-github",
        json={
            "url": "https://github.com/coderamp-labs/gitingest",
            "token": None,
            "include_submodules": False,
            "include_gitignored": False,
        },
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["success"] is True
    assert data["markdown"].startswith("# repo digest")
    assert data["length"] > 0

    from pathlib import Path

    assert Path(data["file_path"]).exists()


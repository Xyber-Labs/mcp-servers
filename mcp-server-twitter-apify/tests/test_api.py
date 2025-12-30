from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from mcp_twitter.app import create_app
from mcp_twitter.twitter import build_default_registry


class FakeScraper:
    def __init__(self, tmp_results_dir: Path):
        self.apify_token = "token"
        self.results_dir = tmp_results_dir
        self.actor_id = "actor"
        self.use_cache = False  # For API compatibility

    def run_query(self, query) -> Path:  # noqa: ANN001
        # Write a deterministic JSON file the API will read back.
        out = self.results_dir / query.output_filename()
        out.write_text(json.dumps([{"id": "1", "text": "hello"}]), encoding="utf-8")
        return out
    
    def get_last_items(self) -> list[dict[str, Any]] | None:
        """Return fake items for API access."""
        return [{"id": "1", "text": "hello"}]


class FakeTwitterScraper(FakeScraper):
    """Matches the constructor the API uses when it creates a temp scraper."""

    def __init__(
        self,
        apify_token: str,  # noqa: ARG002
        results_dir: Path | None,
        actor_name: str,  # noqa: ARG002
        output_format: str = "min",  # noqa: ARG002
        use_cache: bool = False,  # noqa: ARG002
    ):
        super().__init__(results_dir or Path("/tmp"))


@pytest.fixture
def client(monkeypatch, tmp_results_dir: Path) -> TestClient:
    # Create app and patch app state instead of module globals
    app = create_app()
    
    # Patch app state for registry and scraper
    app.state.registry = build_default_registry()
    app.state.scraper = FakeScraper(tmp_results_dir)
    
    # Patch TwitterScraper class for tests
    from mcp_twitter.twitter import scraper as scraper_mod
    monkeypatch.setattr(scraper_mod, "TwitterScraper", FakeTwitterScraper)
    
    return TestClient(app)


def test_health(client: TestClient) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"


def test_root(client: TestClient) -> None:
    r = client.get("/")
    assert r.status_code == 200
    body = r.json()
    assert body["service"] == "Twitter Scraper API"


def test_list_types(client: TestClient) -> None:
    r = client.get("/api/v1/types")
    assert r.status_code == 200
    types = {t["type"] for t in r.json()}
    assert {"topic", "profile", "replies"} <= types


def test_list_queries(client: TestClient) -> None:
    r = client.get("/api/v1/queries")
    assert r.status_code == 200
    assert any(q["id"] == "1" for q in r.json())


def test_search_topic_uses_fake_scraper_and_returns_items(client: TestClient) -> None:
    r = client.post(
        "/hybrid/v1/search/topic",
        json={
            "topic": "Quantum",
            "max_items": 2,
            "sort": "Latest",
            "only_verified": False,
            "only_image": False,
            "lang": "en",
            "output_format": "min",
        },
    )
    assert r.status_code == 200
    items: list[dict[str, Any]] = r.json()
    assert items and items[0]["id"] == "1"


def test_list_results(client: TestClient) -> None:
    """Test that results endpoint returns cache status."""
    r = client.get("/api/v1/results")
    assert r.status_code == 200
    result = r.json()
    assert "message" in result or "cache_enabled" in result


def test_search_profile_batch_returns_items_per_username(client: TestClient) -> None:
    r = client.post(
        "/hybrid/v1/search/profile/batch",
        json={
            "usernames": ["elonmusk", "@jack"],
            "max_items": 2,
            "lang": "en",
            "output_format": "min",
            "continue_on_error": True,
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, list) and len(body) == 2
    assert body[0]["username"] == "elonmusk"
    assert body[1]["username"] == "jack"
    assert body[0]["items"] and body[0]["items"][0]["id"] == "1"
    assert body[0]["error"] is None


def test_search_profile_batch_continue_on_error_returns_error_entry(
    client: TestClient, monkeypatch
) -> None:
    from mcp_twitter.twitter import TwitterScraper
    from mcp_twitter.twitter import scraper as scraper_mod
    
    class ErroringFakeTwitterScraper(TwitterScraper):  # type: ignore[misc]
        def run_query(self, query) -> Path:  # noqa: ANN001
            term = ""
            try:
                term = query.input.searchTerms[0]
            except Exception:
                term = ""
            if "from:baduser" in term:
                raise ValueError("boom")
            return super().run_query(query)

    monkeypatch.setattr(scraper_mod, "TwitterScraper", ErroringFakeTwitterScraper)

    r = client.post(
        "/hybrid/v1/search/profile/batch",
        json={
            "usernames": ["gooduser", "baduser"],
            "max_items": 2,
            "lang": "en",
            "output_format": "min",
            "continue_on_error": True,
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body[0]["username"] == "gooduser"
    assert body[0]["error"] is None
    assert body[1]["username"] == "baduser"
    assert body[1]["items"] == []
    assert body[1]["error"] == "boom"


def test_search_profile_batch_splits_comma_separated_usernames(client: TestClient) -> None:
    r = client.post(
        "/hybrid/v1/search/profile/batch",
        json={
            "usernames": ["elonmusk, xybrainz"],
            "max_items": 2,
            "lang": "en",
            "output_format": "min",
            "continue_on_error": True,
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert [row["username"] for row in body] == ["elonmusk", "xybrainz"]


def test_search_profile_latest_batch_returns_items_per_username(client: TestClient) -> None:
    r = client.post(
        "/hybrid/v1/search/profile/latest/batch",
        json={
            "usernames": ["elonmusk", "@jack"],
            "max_items": 2,
            "lang": "en",
            "output_format": "min",
            "continue_on_error": True,
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, list) and len(body) == 2
    assert body[0]["username"] == "elonmusk"
    assert body[1]["username"] == "jack"
    assert body[0]["items"] and body[0]["items"][0]["id"] == "1"
    assert body[0]["error"] is None


def test_search_profile_latest_batch_splits_comma_separated_usernames(client: TestClient) -> None:
    r = client.post(
        "/hybrid/v1/search/profile/latest/batch",
        json={
            "usernames": ["elonmusk, xybrainz"],
            "max_items": 2,
            "lang": "en",
            "output_format": "min",
            "continue_on_error": True,
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert [row["username"] for row in body] == ["elonmusk", "xybrainz"]


def test_get_results_deprecated(client: TestClient) -> None:
    """Test that file-based results endpoint is deprecated."""
    r = client.get("/api/v1/results/test.json")
    assert r.status_code == 410  # Gone



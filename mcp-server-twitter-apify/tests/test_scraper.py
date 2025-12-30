from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import mcp_twitter.twitter.scraper as scraper_mod
from mcp_twitter.twitter import QueryDefinition, TwitterScraper, TwitterScraperInput

from tests.fakes import FakeApifyClient


def test_minimize_item_keeps_high_signal_fields_and_compacts_author() -> None:
    item: dict[str, Any] = {
        "id": "t1",
        "url": "https://x.com/...",
        "text": "short",
        "fullText": "long",
        "retweetCount": 1,
        "replyCount": 2,
        "likeCount": 3,
        "quoteCount": 4,
        "viewCount": 5,
        "createdAt": "2025-01-01T00:00:00.000Z",
        "author": {
            "id": "a1",
            "userName": "u",
            "name": "User",
            "twitterUrl": "https://x.com/u",
            "extra": "ignored",
        },
        "extraField": "ignored",
    }
    out = TwitterScraper._minimize_item(item)
    assert out["id"] == "t1"
    assert out["author"] == {"id": "a1", "userName": "u", "name": "User", "url": "https://x.com/u"}
    assert "extraField" not in out


def test_run_saves_json_and_minimizes_when_output_format_min(
    monkeypatch, tmp_results_dir: Path
) -> None:
    fake_items = [
        {"id": "1", "text": "hi", "author": {"userName": "u1"}, "likeCount": 2},
        {"id": "2", "text": "yo", "author": {"userName": "u2"}, "likeCount": 3, "extra": "x"},
    ]
    fake_client = FakeApifyClient(dataset_id="ds1", items=fake_items)

    s = TwitterScraper(
        apify_token="token",
        results_dir=tmp_results_dir,
        actor_name="apidojo/twitter-scraper-lite",
        output_format="min",
        use_cache=False,
    )

    # Patch the client on the scraper instance after it's created
    monkeypatch.setattr(s, "client", fake_client)

    out_path = s.run(TwitterScraperInput(searchTerms=["hi"], maxItems=2), output_filename="out")
    assert out_path.exists()
    assert out_path.name == "out.json"

    data = json.loads(out_path.read_text(encoding="utf-8"))
    assert isinstance(data, list)
    assert data[0]["id"] == "1"
    assert "extra" not in data[1]
    assert fake_client.actor_ids == ["apidojo/twitter-scraper-lite"]
    assert fake_client.calls and fake_client.calls[0]["searchTerms"] == ["hi"]


def test_run_saves_raw_when_output_format_max(monkeypatch, tmp_results_dir: Path) -> None:
    fake_items = [{"id": "1", "text": "hi", "extra": {"nested": True}}]
    fake_client = FakeApifyClient(dataset_id="ds1", items=fake_items)

    s = TwitterScraper(
        apify_token="token",
        results_dir=tmp_results_dir,
        actor_name="actor",
        output_format="max",
        use_cache=False,
    )

    # Patch the client on the scraper instance after it's created
    monkeypatch.setattr(s, "client", fake_client)

    out_path = s.run(TwitterScraperInput(searchTerms=["hi"]))
    data = json.loads(out_path.read_text(encoding="utf-8"))
    assert data == fake_items


def test_run_query_uses_query_output_filename(monkeypatch, tmp_results_dir: Path) -> None:
    # Avoid Apify; just stub run()
    s = TwitterScraper(apify_token="token", results_dir=tmp_results_dir, actor_name="actor", use_cache=False)

    def fake_run(
        run_input: TwitterScraperInput,
        output_filename: str | None = None,
        query_type: str | None = None,  # noqa: ARG001
    ) -> Path:
        assert run_input.searchTerms == ["x"]
        assert output_filename == "q.json"
        p = tmp_results_dir / "q.json"
        p.write_text("[]", encoding="utf-8")
        return p

    monkeypatch.setattr(s, "run", fake_run)
    q = QueryDefinition(
        id="1",
        type="topic",
        name="n",
        input=TwitterScraperInput(searchTerms=["x"]),
        output="q.json",
    )
    out_path = s.run_query(q)
    assert out_path.name == "q.json"



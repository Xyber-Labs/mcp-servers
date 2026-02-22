from __future__ import annotations

from typing import Any

from mcp_twitter.twitter import TwitterScraper, TwitterScraperInput
from tests.unit.fakes import FakeApifyClient


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
    assert out["author"] == {
        "id": "a1",
        "userName": "u",
        "name": "User",
        "url": "https://x.com/u",
    }
    assert "extraField" not in out


def test_run_returns_minimized_items_when_output_format_min(monkeypatch) -> None:
    fake_items = [
        {"id": "1", "text": "hi", "author": {"userName": "u1"}, "likeCount": 2},
        {
            "id": "2",
            "text": "yo",
            "author": {"userName": "u2"},
            "likeCount": 3,
            "extra": "x",
        },
    ]
    fake_client = FakeApifyClient(dataset_id="ds1", items=fake_items)

    s = TwitterScraper(
        apify_token="token",
        actor_name="apidojo/twitter-scraper-lite",
        output_format="min",
    )

    # Patch the client on the scraper instance after it's created
    monkeypatch.setattr(s, "client", fake_client)

    items = s.run(TwitterScraperInput(searchTerms=["hi"], maxItems=2))

    assert isinstance(items, list)
    assert items[0]["id"] == "1"
    assert "extra" not in items[1]
    assert fake_client.actor_ids == ["apidojo/twitter-scraper-lite"]
    assert fake_client.calls and fake_client.calls[0]["searchTerms"] == ["hi"]


def test_run_returns_raw_items_when_output_format_max(monkeypatch) -> None:
    fake_items = [{"id": "1", "text": "hi", "extra": {"nested": True}}]
    fake_client = FakeApifyClient(dataset_id="ds1", items=fake_items)

    s = TwitterScraper(
        apify_token="token",
        actor_name="actor",
        output_format="max",
    )

    # Patch the client on the scraper instance after it's created
    monkeypatch.setattr(s, "client", fake_client)

    items = s.run(TwitterScraperInput(searchTerms=["hi"]))
    assert items == fake_items

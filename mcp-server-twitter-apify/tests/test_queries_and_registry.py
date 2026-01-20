from __future__ import annotations

import mcp_twitter.twitter.queries as queries
from mcp_twitter.twitter import QueryRegistry


def test_build_default_registry_has_expected_types_and_ids() -> None:
    reg = queries.build_default_registry()
    assert set(reg.types()) == {"topic", "profile", "replies"}
    assert reg.get("1") is not None
    assert reg.get("2") is not None
    assert reg.get("5") is not None


def test_create_topic_query_builds_expected_input_and_output(monkeypatch, fixed_datetime) -> None:
    monkeypatch.setattr(queries, "datetime", fixed_datetime)
    q = queries.create_topic_query(
        "AI news",
        max_items=50,
        sort="Top",
        only_verified=True,
        only_image=True,
        lang="en",
    )
    assert q.type == "topic"
    assert q.input.searchTerms == ["AI news"]
    assert q.input.sort == "Top"
    assert q.input.maxItems == 50
    assert q.input.tweetLanguage == "en"
    assert q.input.onlyVerifiedUsers is True
    assert q.input.onlyImage is True
    assert q.output == "topic_AI_news_20250101_010203.json"


def test_create_profile_query_strips_at_and_adds_date_range(monkeypatch, fixed_datetime) -> None:
    monkeypatch.setattr(queries, "datetime", fixed_datetime)
    q = queries.create_profile_query(
        "@elonmusk",
        max_items=200,
        since="2025-12-01",
        until="2025-12-31",
        lang="en",
    )
    assert q.type == "profile"
    assert q.input.searchTerms == ["from:elonmusk since:2025-12-01 until:2025-12-31"]
    assert q.input.maxItems == 200
    assert q.output.startswith("profile_elonmusk_2025-12-01_2025-12-31_")
    assert q.output.endswith("_20250101_010203.json")


def test_create_replies_query_builds_conversation_id(monkeypatch, fixed_datetime) -> None:
    monkeypatch.setattr(queries, "datetime", fixed_datetime)
    q = queries.create_replies_query("12345", max_items=10, lang="en")
    assert q.type == "replies"
    assert q.input.searchTerms == ["conversation_id:12345"]
    assert q.input.maxItems == 10
    assert q.output == "replies_12345_20250101_010203.json"


def test_registry_forces_query_type_to_match_container() -> None:
    q = queries.create_topic_query("x")
    q.type = "profile"  # simulate mismatch
    reg = QueryRegistry({"topic": [q]})
    assert reg.get(q.id) is not None
    assert reg.get(q.id).type == "topic"



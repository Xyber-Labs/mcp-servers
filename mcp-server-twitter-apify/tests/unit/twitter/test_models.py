from __future__ import annotations

from mcp_twitter.twitter.models import QueryDefinition, TwitterScraperInput


class TestQueryDefinitionCacheKey:
    """Tests for QueryDefinition.cache_key computed field."""

    def test_cache_key_is_deterministic(self):
        """Same query params produce same cache_key."""
        q1 = QueryDefinition(
            id="1",
            type="topic",
            name="test",
            input=TwitterScraperInput(
                searchTerms=["test"], maxItems=100, sort="Latest"
            ),
        )
        q2 = QueryDefinition(
            id="2",
            type="topic",
            name="different",
            input=TwitterScraperInput(
                searchTerms=["test"], maxItems=100, sort="Latest"
            ),
        )

        # Same type + input = same key (id/name are ignored)
        assert q1.cache_key == q2.cache_key

    def test_cache_key_differs_by_input_params(self):
        """Different input params produce different cache_key."""
        q1 = QueryDefinition(
            id="1",
            type="topic",
            name="test",
            input=TwitterScraperInput(
                searchTerms=["test"], maxItems=100, sort="Latest"
            ),
        )
        q2 = QueryDefinition(
            id="1",
            type="topic",
            name="test",
            input=TwitterScraperInput(searchTerms=["test"], maxItems=50, sort="Latest"),
        )

        assert q1.cache_key != q2.cache_key

    def test_cache_key_differs_by_type(self):
        """Different query types produce different cache_key."""
        input_params = TwitterScraperInput(searchTerms=["test"], maxItems=100)

        q_topic = QueryDefinition(id="1", type="topic", name="t", input=input_params)
        q_profile = QueryDefinition(
            id="2", type="profile", name="p", input=input_params
        )
        q_replies = QueryDefinition(
            id="3", type="replies", name="r", input=input_params
        )

        assert q_topic.cache_key != q_profile.cache_key
        assert q_profile.cache_key != q_replies.cache_key
        assert q_topic.cache_key != q_replies.cache_key

    def test_cache_key_is_sha256_hex(self):
        """Cache key is a 64-character SHA256 hex string."""
        q = QueryDefinition(
            id="1",
            type="topic",
            name="test",
            input=TwitterScraperInput(searchTerms=["test"]),
        )

        assert len(q.cache_key) == 64
        assert all(c in "0123456789abcdef" for c in q.cache_key)

    def test_cache_key_ignores_none_params(self):
        """None parameters are excluded from cache key calculation."""
        q1 = QueryDefinition(
            id="1",
            type="topic",
            name="test",
            input=TwitterScraperInput(searchTerms=["test"], maxItems=None),
        )
        q2 = QueryDefinition(
            id="2",
            type="topic",
            name="other",
            input=TwitterScraperInput(searchTerms=["test"]),
        )

        # Both should produce the same key since maxItems=None is excluded
        assert q1.cache_key == q2.cache_key

    def test_cache_key_differs_by_sort_order(self):
        """Different sort orders produce different cache_key."""
        q_latest = QueryDefinition(
            id="1",
            type="topic",
            name="test",
            input=TwitterScraperInput(searchTerms=["test"], sort="Latest"),
        )
        q_top = QueryDefinition(
            id="1",
            type="topic",
            name="test",
            input=TwitterScraperInput(searchTerms=["test"], sort="Top"),
        )

        assert q_latest.cache_key != q_top.cache_key

from __future__ import annotations

from datetime import datetime
from typing import Any

from mcp_twitter.twitter.models import QueryDefinition, SortOrder, TwitterScraperInput
from mcp_twitter.twitter.registry import QueryRegistry


def build_default_registry() -> QueryRegistry:
    return QueryRegistry(
        queries_by_type={
            "topic": [
                QueryDefinition(
                    id="1",
                    type="topic",
                    name="Keyword Search: 'apify' (Latest, English, Verified users)",
                    input=TwitterScraperInput(
                        searchTerms=["apify"],
                        sort="Latest",
                        maxItems=100,
                        tweetLanguage="en",
                        onlyVerifiedUsers=True,
                        maxTweets=1000,
                    ),
                    output="topic_apify.json",
                ),
                QueryDefinition(
                    id="4",
                    type="topic",
                    name="Topic Search: 'AI news' (Verified + Images)",
                    input=TwitterScraperInput(
                        searchTerms=["AI news"],
                        sort="Top",
                        maxItems=100,
                        tweetLanguage="en",
                        onlyVerifiedUsers=True,
                        onlyImage=True,
                    ),
                    output="topic_ai_news.json",
                ),
            ],
            "profile": [
                QueryDefinition(
                    id="2",
                    type="profile",
                    name="Profile Tweets: from:elonmusk (Latest 100)",
                    input=TwitterScraperInput(
                        searchTerms=["from:elonmusk"],
                        sort="Latest",
                        maxItems=100,
                        tweetLanguage="en",
                    ),
                    output="profile_elonmusk.json",
                ),
                QueryDefinition(
                    id="3",
                    type="profile",
                    name="Profile Tweets Dec 2025: from:elonmusk",
                    input=TwitterScraperInput(
                        searchTerms=["from:elonmusk since:2025-12-01 until:2025-12-31"],
                        sort="Latest",
                        maxItems=800,
                        tweetLanguage="en",
                    ),
                    output="profile_elonmusk_dec2025.json",
                ),
            ],
            "replies": [
                QueryDefinition(
                    id="5",
                    type="replies",
                    name="Replies to Tweet (conversation_id)",
                    input=TwitterScraperInput(
                        searchTerms=["conversation_id:1728108619189874825"],
                        sort="Latest",
                        maxItems=50,
                        tweetLanguage="en",
                    ),
                    output="replies_conversation.json",
                )
            ],
        }
    )


def _safe_slug(s: str) -> str:
    return s.strip().replace(" ", "_").replace(":", "_")


def create_topic_query(
    topic: str,
    *,
    max_items: int = 100,
    sort: SortOrder = "Latest",
    only_verified: bool = False,
    only_image: bool = False,
    lang: str = "en",
) -> QueryDefinition:
    query_input: dict[str, Any] = {
        "searchTerms": [topic],
        "sort": sort,
        "maxItems": max_items,
        "tweetLanguage": lang,
    }
    if only_verified:
        query_input["onlyVerifiedUsers"] = True
    if only_image:
        query_input["onlyImage"] = True

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return QueryDefinition(
        id="custom",
        type="topic",
        name=f"Custom Topic Search: '{topic}'",
        input=TwitterScraperInput(**query_input),
        output=f"topic_{_safe_slug(topic)}_{ts}.json",
    )


def create_profile_query(
    username: str,
    *,
    max_items: int = 100,
    since: str | None = None,
    until: str | None = None,
    lang: str = "en",
) -> QueryDefinition:
    username = username.lstrip("@")
    search_term = f"from:{username}"
    if since and until:
        search_term += f" since:{since} until:{until}"
    elif since:
        search_term += f" since:{since}"
    elif until:
        search_term += f" until:{until}"

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = f"_{since}_{until}" if (since or until) else ""
    return QueryDefinition(
        id="custom",
        type="profile",
        name=f"Custom Profile Search: @{username}",
        input=TwitterScraperInput(
            searchTerms=[search_term],
            sort="Latest",
            maxItems=max_items,
            tweetLanguage=lang,
        ),
        output=f"profile_{_safe_slug(username)}{suffix}_{ts}.json",
    )


def create_replies_query(
    conversation_id: str,
    *,
    max_items: int = 50,
    lang: str = "en",
) -> QueryDefinition:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return QueryDefinition(
        id="custom",
        type="replies",
        name=f"Custom Replies Search: conversation_id:{conversation_id}",
        input=TwitterScraperInput(
            searchTerms=[f"conversation_id:{conversation_id}"],
            sort="Latest",
            maxItems=max_items,
            tweetLanguage=lang,
        ),
        output=f"replies_{_safe_slug(conversation_id)}_{ts}.json",
    )



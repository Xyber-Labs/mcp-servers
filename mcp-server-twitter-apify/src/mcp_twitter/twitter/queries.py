from __future__ import annotations

from typing import Any

from mcp_twitter.twitter.models import QueryDefinition, SortOrder, TwitterScraperInput


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

    return QueryDefinition(
        id="custom",
        type="topic",
        name=f"Custom Topic Search: '{topic}'",
        input=TwitterScraperInput(**query_input),
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
    )


def create_replies_query(
    conversation_id: str,
    *,
    max_items: int = 50,
    lang: str = "en",
) -> QueryDefinition:
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
    )

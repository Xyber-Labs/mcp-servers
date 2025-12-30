"""
This module implements MCP-only tools for Twitter analysis, designed specifically for AI agents.

Main responsibility: Provide premium analysis tools that synthesize Twitter data into insights
optimized for AI agent consumption. These tools require x402 payment and are not exposed as REST endpoints.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter()


def _get_scraper(request: Request):
    """Get scraper from app state."""
    scraper = getattr(request.app.state, "scraper", None)
    if not scraper:
        raise HTTPException(status_code=500, detail="Scraper not initialized")
    return scraper


class TweetSummarizationRequest(BaseModel):
    """Request model for tweet summarization."""

    topic: str = Field(..., description="Topic or keyword to search for")
    max_items: int = Field(10, ge=1, le=100, description="Maximum tweets to analyze")
    sort: str = Field("Top", description="Sort order: Latest or Top")


@router.post(
    "/summarize_tweets",
    tags=["Agent Utilities"],
    # IMPORTANT: The `operation_id` is crucial. It's used by the x402 middleware
    # and the dynamic pricing configuration in `tool_pricing.yaml` to identify this
    # specific tool for payment. It must be unique across all endpoints.
    operation_id="summarize_tweets",
)
async def summarize_tweets(
    request: TweetSummarizationRequest,
    http_request: Request,
) -> dict[str, Any]:
    """
    Provides a comprehensive summary and analysis of tweets for a given topic.

    This premium tool analyzes multiple tweets on a topic and synthesizes them into
    a structured summary optimized for AI agent consumption. It requires x402 payment
    and is not exposed as a REST endpoint because it's specifically designed for
    LLM reasoning and decision-making.

    The analysis includes:
    - Key themes and topics discussed
    - Sentiment overview
    - Notable mentions and trends
    - Summary statistics
    """
    try:
        logger.info(f"Performing paid tweet analysis for topic: {request.topic}")

        scraper = _get_scraper(http_request)

        # Create a topic query to fetch tweets
        from mcp_twitter.twitter import QueryDefinition, TwitterScraperInput, create_topic_query

        query = create_topic_query(
            topic=request.topic,
            max_items=request.max_items,
            sort=request.sort,
            only_verified=False,
            only_image=False,
            lang="en",
            output_format="min",
        )

        # Run the query (uses cache if available)
        scraper.run_query(query)
        items = scraper.get_last_items()

        if not items:
            return {
                "topic": request.topic,
                "summary": f"No tweets found for topic '{request.topic}'.",
                "tweet_count": 0,
                "key_themes": [],
                "sentiment": "neutral",
                "notable_mentions": [],
            }

        # Analyze tweets
        tweet_count = len(items)
        texts = [item.get("text", "") or item.get("fullText", "") for item in items if isinstance(item, dict)]
        
        # Extract key themes (simplified - in production, use NLP)
        key_themes = []
        if texts:
            # Simple keyword extraction (in production, use proper NLP)
            all_words = " ".join(texts).lower().split()
            common_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", "is", "are", "was", "were", "be", "been", "have", "has", "had", "do", "does", "did", "will", "would", "could", "should", "may", "might", "must", "can", "this", "that", "these", "those", "i", "you", "he", "she", "it", "we", "they", "http", "https", "com", "www"}
            word_freq = {}
            for word in all_words:
                if len(word) > 3 and word not in common_words:
                    word_freq[word] = word_freq.get(word, 0) + 1
            key_themes = [word for word, count in sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:5]]

        # Extract notable mentions (usernames)
        notable_mentions = []
        for item in items:
            if isinstance(item, dict):
                author = item.get("author", {})
                if isinstance(author, dict):
                    username = author.get("userName")
                    if username:
                        notable_mentions.append(username)
        notable_mentions = list(set(notable_mentions))[:10]

        # Simple sentiment analysis (in production, use proper sentiment analysis)
        positive_words = {"good", "great", "excellent", "amazing", "love", "best", "awesome", "fantastic", "wonderful", "happy"}
        negative_words = {"bad", "terrible", "awful", "hate", "worst", "horrible", "sad", "angry", "disappointed"}
        
        all_text_lower = " ".join(texts).lower()
        positive_count = sum(1 for word in positive_words if word in all_text_lower)
        negative_count = sum(1 for word in negative_words if word in all_text_lower)
        
        if positive_count > negative_count:
            sentiment = "positive"
        elif negative_count > positive_count:
            sentiment = "negative"
        else:
            sentiment = "neutral"

        # Generate summary
        summary = (
            f"Analysis of {tweet_count} tweets about '{request.topic}':\n\n"
            f"The discussion primarily revolves around {', '.join(key_themes[:3]) if key_themes else 'various topics'}.\n"
            f"Overall sentiment appears to be {sentiment}.\n"
            f"{len(notable_mentions)} distinct users contributed to the conversation."
        )

        return {
            "topic": request.topic,
            "summary": summary,
            "tweet_count": tweet_count,
            "key_themes": key_themes[:5],
            "sentiment": sentiment,
            "notable_mentions": notable_mentions[:10],
            "analysis_metadata": {
                "sort_order": request.sort,
                "max_items_requested": request.max_items,
                "items_analyzed": tweet_count,
            },
        }

    except Exception as e:
        logger.error(f"Error in summarize_tweets: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to generate tweet analysis: {str(e)}"
        )


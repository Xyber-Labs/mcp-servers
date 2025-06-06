import json
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, List, Optional, Literal

from fastmcp import FastMCP, Context
from fastmcp.exceptions import ToolError

from .twitter import AsyncTwitterClient, get_twitter_client

logger = logging.getLogger(__name__)





# --- Lifespan Management --- #
@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[dict[str, Any]]:
    """Manage server startup/shutdown. Initializes the Twitter client."""
    logger.info("Lifespan: Initializing Twitter client...")
    
    try:
        # Initialize Twitter client
        twitter_client: AsyncTwitterClient = await get_twitter_client()
        
        logger.info("Lifespan: Twitter client initialized successfully")
        yield {"twitter_client": twitter_client}
    
    except Exception as init_err:
        logger.error(f"FATAL: Lifespan initialization failed: {init_err}", exc_info=True)
        raise init_err
    
    finally:
        logger.info("Lifespan: Shutdown cleanup completed")


# --- MCP Server Initialization --- #
mcp_server = FastMCP("twitter-server", lifespan=app_lifespan)


# --- Tool Definitions --- #

@mcp_server.tool()
async def create_tweet(
    ctx: Context,
    text: str,
    image_content_str: Optional[str] = None,
    poll_options: Optional[List[str]] = None,
    poll_duration: Optional[int] = None,
    in_reply_to_tweet_id: Optional[str] = None,
    quote_tweet_id: Optional[str] = None
) -> str:
    """
    Create a new tweet with optional media, polls, replies or quotes.

    Args:
        text: The text content of the tweet. Will be truncated to the configured maximum tweet length if necessary.
        image_content_str: A Base64-encoded string of image data to attach as media. Requires media uploads to be enabled in config.
        poll_options: A list of 2 to 4 options to include in a poll.
        poll_duration: Duration of the poll in minutes (must be between 5 and 10080).
        in_reply_to_tweet_id: The ID of an existing tweet to reply to. Note: Your text must include "@username" of the tweet's author.
        quote_tweet_id: The ID of an existing tweet to quote. The quoted tweet will appear inline, with your text shown above it.

    Returns:
        Success message with tweet ID or error message.
    """
    client = ctx.request_context.lifespan_context["twitter_client"]
    
    try:
        # Validate inputs
        if poll_options and (len(poll_options) < 2 or len(poll_options) > 4):
            raise ToolError("Poll must have 2-4 options")
        
        if poll_options and poll_duration and (poll_duration < 5 or poll_duration > 10080):
            raise ToolError("Poll duration must be 5-10080 minutes")
        
        # Create tweet
        result = await client.create_tweet(
            text=text,
            image_content_str=image_content_str,
            poll_options=poll_options,
            poll_duration=poll_duration,
            in_reply_to_tweet_id=in_reply_to_tweet_id,
            quote_tweet_id=quote_tweet_id
        )
        
        # Check if the result is an error string or a tweet ID
        if isinstance(result, str) and ("Error" in result or "error" in result):
            raise ToolError(f"Tweet creation failed: {result}")
        else:
            return f"Tweet created successfully with ID: {result}"
            
    except ToolError:
        raise
    except Exception as e:
        error_msg = str(e)
        if "403" in error_msg or "Forbidden" in error_msg:
            raise ToolError("Tweet creation forbidden. Check content policy or API permissions")
        elif "401" in error_msg or "Unauthorized" in error_msg:
            raise ToolError("Unauthorized. Check Twitter API credentials and permissions")
        elif "duplicate" in error_msg.lower():
            raise ToolError("Duplicate tweet. This content has already been posted")
        else:
            raise ToolError(f"Error creating tweet: {error_msg}")


@mcp_server.tool()
async def get_user_tweets(
    ctx: Context,
    user_ids: List[str],
    max_results: int = 10
) -> str:
    """
    Retrieve recent tweets posted by a list of users.

    Args:
        user_ids: The IDs of the users whose tweets to fetch.
        max_results: The maximum number of tweets to return per user. Must be between 1 and 100.

    Returns:
        JSON string mapping user IDs to lists of tweet texts or error messages.
    """
    client = ctx.request_context.lifespan_context["twitter_client"]
    
    try:
        tweets_dict: dict[str, list[str]] = {}
        
        for uid in user_ids:
            try:
                resp = await client.get_user_tweets(
                    user_id=uid,
                    max_results=max_results
                )
                
                if resp and resp.data:
                    tweets_dict[uid] = [t.text for t in resp.data]
                else:
                    tweets_dict[uid] = []
                    
            except Exception as user_error:
                # Handle individual user errors gracefully
                error_msg = str(user_error)
                if "401" in error_msg or "Unauthorized" in error_msg:
                    tweets_dict[uid] = [f"Error: Unauthorized access. Twitter API permissions may be insufficient to read tweets for user {uid}"]
                elif "404" in error_msg or "Not Found" in error_msg:
                    tweets_dict[uid] = [f"Error: User {uid} not found or account is private/suspended"]
                elif "403" in error_msg or "Forbidden" in error_msg:
                    tweets_dict[uid] = [f"Error: Access forbidden for user {uid}. Account may be private or protected"]
                else:
                    tweets_dict[uid] = [f"Error retrieving tweets for user {uid}: {error_msg}"]
                logger.warning(f"Failed to get tweets for user {uid}: {error_msg}")
        
        return json.dumps(tweets_dict, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"Unexpected error in get_user_tweets: {str(e)}", exc_info=True)
        raise ToolError(f"Error retrieving tweets: {str(e)}")


@mcp_server.tool()
async def follow_user(
    ctx: Context,
    user_id: str
) -> str:
    """
    Follow another Twitter user by their user ID.

    Args:
        user_id: The ID of the user to follow.

    Returns:
        Success message confirming the follow.
    """
    client = ctx.request_context.lifespan_context["twitter_client"]
    
    try:
        response = await client.follow_user(user_id)
        return f"Following user: {response}"
        
    except Exception as follow_error:
        error_msg = str(follow_error)
        if "404" in error_msg or "Not Found" in error_msg:
            raise ToolError(f"User {user_id} not found")
        elif "403" in error_msg or "Forbidden" in error_msg:
            raise ToolError(f"Cannot follow user {user_id}. Account may be private or you may already be following them")
        elif "401" in error_msg or "Unauthorized" in error_msg:
            raise ToolError("Unauthorized. Check Twitter API permissions for following users")
        else:
            raise ToolError(f"Error following user {user_id}: {error_msg}")


@mcp_server.tool()
async def retweet_tweet(
    ctx: Context,
    tweet_id: str
) -> str:
    """
    Retweet an existing tweet on behalf of the authenticated user.

    Args:
        tweet_id: The ID of the tweet to retweet.

    Returns:
        Success message confirming the retweet.
    """
    client = ctx.request_context.lifespan_context["twitter_client"]
    
    try:
        response = await client.retweet_tweet(tweet_id)
        return f"Retweeting tweet: {response}"
        
    except Exception as retweet_error:
        error_msg = str(retweet_error)
        if "404" in error_msg or "Not Found" in error_msg:
            raise ToolError(f"Tweet {tweet_id} not found or has been deleted")
        elif "403" in error_msg or "Forbidden" in error_msg:
            raise ToolError(f"Cannot retweet {tweet_id}. Tweet may be private or you may have already retweeted it")
        elif "401" in error_msg or "Unauthorized" in error_msg:
            raise ToolError("Unauthorized. Check Twitter API permissions for retweeting")
        else:
            raise ToolError(f"Error retweeting {tweet_id}: {error_msg}")




import asyncio
import base64
import io
import logging
import ssl
import os
import time

import aiohttp
import anyio
import requests
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)
from tweepy import API, OAuth1UserHandler
from tweepy.asynchronous import AsyncClient
from tweepy.errors import TweepyException
from typing import List, Dict

from mcp_server_twitter.logging_config import configure_logging
from mcp_server_twitter.helpers import convert_base64_to_image, validate_poll_parameters, load_country_codes

from mcp_server_twitter.exceptions import (
    BaseMCPException, 
    ServiceUnavailableError, 
    InvalidResponseError, 
    AuthenticationError, 
    ValidationError, 
    RateLimitError
)

logger = logging.getLogger(__name__)


def is_retryable_tweepy_error(exception: Exception) -> bool:
    """Return True if the exception is a TweepyException with a 5xx status code."""
    if not isinstance(exception, TweepyException):
        return False

    response = getattr(exception, "response", None)
    if response is None:
        return False

    return 500 <= response.status_code < 600


# Enhanced retry decorator with better logging
retry_async_wrapper = retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(min=0.5, max=10),
    retry=retry_if_exception_type(aiohttp.ClientError)
    | retry_if_exception(is_retryable_tweepy_error),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)

retry_sync_in_async_wrapper = retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(min=0.5, max=10),
    retry=retry_if_exception_type(requests.exceptions.RequestException)
    | retry_if_exception(is_retryable_tweepy_error),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)


def handle_tweepy_exception(e: TweepyException, operation: str) -> BaseMCPException:
    """Convert TweepyException to custom exception with context."""
    error_msg = str(e).lower()
    response = getattr(e, "response", None)
    status_code = response.status if response else None
    
    logger.warning("Handling Tweepy exception", extra={
        "operation": operation,
        "error_type": type(e).__name__,
        "status_code": status_code,
        "error_message": error_msg[:200]  # Truncate for logging
    })
    
    if status_code == 429 or "rate limit" in error_msg:
        return RateLimitError(f"Twitter API rate limit exceeded for {operation}")
    elif status_code == 401 or "unauthorized" in error_msg:
        return AuthenticationError(f"Unauthorized access for {operation}")
    elif status_code == 403 or "forbidden" in error_msg:
        return ValidationError(f"Forbidden action for {operation}")
    elif status_code == 404 or "not found" in error_msg:
        return ValidationError(f"Resource not found for {operation}")
    elif status_code and 500 <= status_code < 600:
        return ServiceUnavailableError(f"Twitter service unavailable for {operation}")
    elif "invalid" in error_msg or "bad request" in error_msg:
        return InvalidResponseError(f"Invalid request for {operation}: {str(e)}")
    else:
        return BaseMCPException(f"Twitter API error for {operation}: {str(e)}")


class AsyncTwitterClient:
    def __init__(self, config):
        """
        Initialize Twitter API client with provided configuration.
        """
        self.config = config

        # Create a custom SSL context
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = True
        self.ssl_context.verify_mode = ssl.CERT_REQUIRED

        try:
            self.client = AsyncClient(
                consumer_key=config.API_KEY,
                consumer_secret=config.API_SECRET_KEY,
                access_token=config.ACCESS_TOKEN,
                access_token_secret=config.ACCESS_TOKEN_SECRET,
                bearer_token=config.BEARER_TOKEN,
                wait_on_rate_limit=True,
            )

            auth = OAuth1UserHandler(config.API_KEY, config.API_SECRET_KEY)
            auth.set_access_token(config.ACCESS_TOKEN, config.ACCESS_TOKEN_SECRET)
            self._sync_api = API(auth, wait_on_rate_limit=True)
            
            logger.info("Twitter client initialized successfully", extra={
                "operation": "client_init",
                "status": "SUCCESS"
            })
            
        except Exception as e:
            logger.error("Failed to initialize Twitter client", exc_info=True, extra={
                "operation": "client_init",
                "status": "ERROR",
                "error_type": type(e).__name__
            })
            raise AuthenticationError(f"Failed to initialize Twitter client: {str(e)}")

    @retry_sync_in_async_wrapper
    async def _upload_media(self, image_file: io.BytesIO):
        """
        Internal method to upload media to Twitter.
        Note: Using sync client as Tweepy doesn't support async media upload yet.
        """
        try:
            logger.debug("Starting media upload", extra={
                "operation": "upload_media",
                "status": "START"
            })
            
            def sync_upload():
                return self._sync_api.media_upload(file=image_file)
            
            # Run sync operation in thread pool
            media = await anyio.to_thread.run_sync(sync_upload)
            
            logger.info("Media upload completed successfully", extra={
                "operation": "upload_media",
                "status": "SUCCESS",
                "media_id": media.media_id
            })
            
            return media.media_id
            
        except TweepyException as e:
            custom_exception = handle_tweepy_exception(e, "upload_media")
            logger.error("Media upload failed", extra={
                "operation": "upload_media",
                "status": "ERROR",
                "error_type": type(custom_exception).__name__
            })
            raise custom_exception
        except Exception as e:
            logger.error("Unexpected error during media upload", exc_info=True, extra={
                "operation": "upload_media",
                "status": "ERROR",
                "error_type": type(e).__name__
            })
            raise BaseMCPException(f"Media upload failed: {str(e)}")

    async def initialize(self):
        """
        Initialize and test the Twitter client connection.
        """
        start_time = time.time()
        
        logger.info("Starting Twitter client initialization", extra={
            "operation": "initialize_client",
            "status": "START"
        })
        
        try:
            user = await self.client.get_me()
            
            logger.info("Twitter client initialization completed successfully", extra={
                "operation": "initialize_client",
                "status": "SUCCESS",
                "duration_ms": round((time.time() - start_time) * 1000, 2),
                "authenticated_user": user.data['username'] if user.data else "unknown"
            })
            
            return self
            
        except TweepyException as e:
            custom_exception = handle_tweepy_exception(e, "initialize_client")
            logger.error("Twitter client initialization failed", extra={
                "operation": "initialize_client",
                "status": "ERROR",
                "duration_ms": round((time.time() - start_time) * 1000, 2),
                "error_type": type(custom_exception).__name__
            })
            raise custom_exception
        except Exception as e:
            logger.error("Twitter client initialization failed", exc_info=True, extra={
                "operation": "initialize_client",
                "status": "ERROR",
                "duration_ms": round((time.time() - start_time) * 1000, 2),
                "system_error": str(e),
                "error_type": type(e).__name__
            })
            raise AuthenticationError(f"Twitter client initialization failed: {str(e)}")

    @retry_async_wrapper
    async def create_tweet(
        self,
        text: str,
        image_content_str: str | None = None,
        poll_options: list[str] | None = None,
        poll_duration: int | None = None,
        in_reply_to_tweet_id: str | None = None,
        quote_tweet_id: str | None = None,
    ) -> str:
        """
        Create a new tweet with optional media, polls, replies or quotes.
        """
        operation_start = time.time()
        
        logger.info("Starting tweet creation", extra={
            "operation": "create_tweet",
            "status": "START",
            "text_length": len(text),
            "has_image": image_content_str is not None,
            "has_poll": poll_options is not None,
            "is_reply": in_reply_to_tweet_id is not None,
            "is_quote": quote_tweet_id is not None
        })

        try:
            # Validate inputs
            if not text.strip():
                raise ValidationError("Tweet text cannot be empty")
                
            # Truncate text if necessary
            if len(text) > self.config.max_tweet_length:
                text = text[:self.config.max_tweet_length]
                logger.warning("Tweet text truncated", extra={
                    "operation": "create_tweet",
                    "original_length": len(text),
                    "truncated_length": self.config.max_tweet_length
                })

            # Prepare tweet parameters
            tweet_params = {"text": text}
            
            # Handle media upload
            media_ids = None
            if image_content_str and self.config.media_upload_enabled:
                try:
                    image_file = convert_base64_to_image(image_content_str)
                    media_id = await self._upload_media(image_file)
                    media_ids = [media_id]
                    logger.debug("Media attached to tweet", extra={
                        "operation": "create_tweet",
                        "media_id": media_id
                    })
                except Exception as e:
                    raise InvalidResponseError(f"Failed to upload image: {str(e)}")

            # Handle poll
            if poll_options and poll_duration:
                try:
                    validate_poll_parameters(poll_options, poll_duration, self.config)
                    tweet_params["poll"] = {
                        "options": poll_options,
                        "duration_minutes": poll_duration
                    }
                    logger.debug("Poll attached to tweet", extra={
                        "operation": "create_tweet",
                        "poll_options_count": len(poll_options),
                        "poll_duration": poll_duration
                    })
                except Exception as e:
                    raise ValidationError(f"Invalid poll parameters: {str(e)}")

            # Handle reply
            if in_reply_to_tweet_id:
                tweet_params["in_reply_to_tweet_id"] = in_reply_to_tweet_id
                logger.debug("Reply tweet configured", extra={
                    "operation": "create_tweet",
                    "reply_to": in_reply_to_tweet_id
                })

            # Handle quote tweet
            if quote_tweet_id:
                tweet_params["quote_tweet_id"] = quote_tweet_id
                logger.debug("Quote tweet configured", extra={
                    "operation": "create_tweet",
                    "quote_tweet": quote_tweet_id
                })

            # Add media if available
            if media_ids:
                tweet_params["media_ids"] = media_ids

            # Create the tweet
            response = await self.client.create_tweet(**tweet_params)
            
            duration_ms = round((time.time() - operation_start) * 1000, 2)
            
            logger.info("Tweet created successfully", extra={
                "operation": "create_tweet",
                "status": "SUCCESS",
                "tweet_id": response.data["id"],
                "duration_ms": duration_ms
            })

            return f"Tweet created successfully! Tweet ID: {response.data['id']}"
            
        except TweepyException as e:
            custom_exception = handle_tweepy_exception(e, "create_tweet")
            duration_ms = round((time.time() - operation_start) * 1000, 2)
            logger.error("Tweet creation failed", extra={
                "operation": "create_tweet",
                "status": "ERROR",
                "duration_ms": duration_ms,
                "error_type": type(custom_exception).__name__
            })
            raise custom_exception
        except BaseMCPException:
            # Re-raise custom exceptions as-is
            raise
        except Exception as e:
            duration_ms = round((time.time() - operation_start) * 1000, 2)
            logger.error("Unexpected error during tweet creation", exc_info=True, extra={
                "operation": "create_tweet",
                "status": "ERROR",
                "duration_ms": duration_ms,
                "error_type": type(e).__name__
            })
            raise BaseMCPException(f"Tweet creation failed: {str(e)}")

    @retry_async_wrapper
    async def search_tweets(self, query: str, max_results: int = 10) -> str:
        """
        Search for tweets matching the given query.
        """
        operation_start = time.time()
        
        logger.info("Starting tweet search", extra={
            "operation": "search_tweets",
            "status": "START",
            "query": query,
            "max_results": max_results
        })

        try:
            # Validate inputs
            if not query.strip():
                raise ValidationError("Search query cannot be empty")
                
            if not (1 <= max_results <= 100):
                raise ValidationError("max_results must be between 1 and 100")

            # Perform search
            response = await self.client.search_recent_tweets(
                query=query,
                max_results=max_results,
                tweet_fields=["created_at", "author_id", "public_metrics", "context_annotations"]
            )

            if not response.data:
                logger.info("No tweets found for search", extra={
                    "operation": "search_tweets",
                    "status": "NO_RESULTS",
                    "query": query
                })
                return f"No tweets found for query: {query}"

            # Format results
            tweets = []
            for tweet in response.data:
                tweet_info = {
                    "id": tweet.id,
                    "text": tweet.text,
                    "created_at": tweet.created_at.isoformat() if tweet.created_at else None,
                    "author_id": tweet.author_id,
                    "public_metrics": tweet.public_metrics if hasattr(tweet, 'public_metrics') else None
                }
                tweets.append(tweet_info)

            duration_ms = round((time.time() - operation_start) * 1000, 2)
            
            logger.info("Tweet search completed successfully", extra={
                "operation": "search_tweets",
                "status": "SUCCESS",
                "tweets_found": len(tweets),
                "duration_ms": duration_ms
            })

            return f"Found {len(tweets)} tweets:\n" + "\n".join([
                f"Tweet {tweet['id']}: {tweet['text'][:100]}..." if len(tweet['text']) > 100 
                else f"Tweet {tweet['id']}: {tweet['text']}"
                for tweet in tweets
            ])
            
        except TweepyException as e:
            custom_exception = handle_tweepy_exception(e, "search_tweets")
            duration_ms = round((time.time() - operation_start) * 1000, 2)
            logger.error("Tweet search failed", extra={
                "operation": "search_tweets",
                "status": "ERROR",
                "duration_ms": duration_ms,
                "error_type": type(custom_exception).__name__
            })
            raise custom_exception
        except BaseMCPException:
            raise
        except Exception as e:
            duration_ms = round((time.time() - operation_start) * 1000, 2)
            logger.error("Unexpected error during tweet search", exc_info=True, extra={
                "operation": "search_tweets",
                "status": "ERROR",
                "duration_ms": duration_ms,
                "error_type": type(e).__name__
            })
            raise BaseMCPException(f"Tweet search failed: {str(e)}")

    @retry_async_wrapper
    async def follow_user(self, user_id: str) -> str:
        """
        Follow a user by their user ID.
        """
        operation_start = time.time()
        
        logger.info("Starting follow user", extra={
            "operation": "follow_user",
            "status": "START",
            "user_id": user_id
        })

        try:
            # Validate input
            if not user_id.strip():
                raise ValidationError("User ID cannot be empty")

            # Follow the user
            response = await self.client.follow_user(user_id)
            
            duration_ms = round((time.time() - operation_start) * 1000, 2)
            
            logger.info("User followed successfully", extra={
                "operation": "follow_user",
                "status": "SUCCESS",
                "user_id": user_id,
                "duration_ms": duration_ms
            })

            return f"Successfully followed user {user_id}"
            
        except TweepyException as e:
            custom_exception = handle_tweepy_exception(e, "follow_user")
            duration_ms = round((time.time() - operation_start) * 1000, 2)
            logger.error("Follow user failed", extra={
                "operation": "follow_user",
                "status": "ERROR",
                "user_id": user_id,
                "duration_ms": duration_ms,
                "error_type": type(custom_exception).__name__
            })
            raise custom_exception
        except BaseMCPException:
            raise
        except Exception as e:
            duration_ms = round((time.time() - operation_start) * 1000, 2)
            logger.error("Unexpected error during follow user", exc_info=True, extra={
                "operation": "follow_user",
                "status": "ERROR",
                "user_id": user_id,
                "duration_ms": duration_ms,
                "error_type": type(e).__name__
            })
            raise BaseMCPException(f"Follow user failed: {str(e)}")

    @retry_async_wrapper
    async def retweet_tweet(self, tweet_id: str) -> str:
        """
        Retweet an existing tweet.
        """
        operation_start = time.time()
        
        logger.info("Starting retweet", extra={
            "operation": "retweet_tweet",
            "status": "START",
            "tweet_id": tweet_id
        })

        try:
            # Validate input
            if not tweet_id.strip():
                raise ValidationError("Tweet ID cannot be empty")

            # Retweet the tweet
            response = await self.client.retweet(tweet_id)
            
            duration_ms = round((time.time() - operation_start) * 1000, 2)
            
            logger.info("Tweet retweeted successfully", extra={
                "operation": "retweet_tweet",
                "status": "SUCCESS",
                "tweet_id": tweet_id,
                "duration_ms": duration_ms
            })

            return f"Successfully retweeted tweet {tweet_id}"
            
        except TweepyException as e:
            custom_exception = handle_tweepy_exception(e, "retweet_tweet")
            duration_ms = round((time.time() - operation_start) * 1000, 2)
            logger.error("Retweet failed", extra={
                "operation": "retweet_tweet",
                "status": "ERROR",
                "tweet_id": tweet_id,
                "duration_ms": duration_ms,
                "error_type": type(custom_exception).__name__
            })
            raise custom_exception
        except BaseMCPException:
            raise
        except Exception as e:
            duration_ms = round((time.time() - operation_start) * 1000, 2)
            logger.error("Unexpected error during retweet", exc_info=True, extra={
                "operation": "retweet_tweet",
                "status": "ERROR",
                "tweet_id": tweet_id,
                "duration_ms": duration_ms,
                "error_type": type(e).__name__
            })
            raise BaseMCPException(f"Retweet failed: {str(e)}")

    @retry_async_wrapper
    async def get_trends(self, countries: list[str], max_trends: int = 50) -> str:
        """
        Get trending topics for specified countries.
        """
        operation_start = time.time()
        
        logger.info("Starting trends retrieval", extra={
            "operation": "get_trends",
            "status": "START",
            "countries": countries,
            "countries_count": len(countries),
            "max_trends": max_trends
        })

        try:
            # Validate inputs
            if not countries:
                raise ValidationError("Countries list cannot be empty")
                
            if not (1 <= max_trends <= 50):
                raise ValidationError("max_trends must be between 1 and 50")

            # Load country codes mapping
            try:
                country_codes = load_country_codes()
            except Exception as e:
                raise InvalidResponseError(f"Failed to load country codes: {str(e)}")

            trends_result = {}
            
            for country in countries:
                country_start_time = time.time()
                
                try:
                    # Get WOEID for country
                    woeid = country_codes.get(country.lower())
                    if not woeid:
                        trends_result[str(country)] = [f"Error: Country '{country}' not found in mapping"]
                        logger.warning("Country not found in mapping", extra={
                            "operation": "get_trends",
                            "country": country
                        })
                        continue

                    # Get trends for this country (using sync API wrapped in thread)
                    def get_country_trends():
                        return self._sync_api.get_place_trends(woeid)

                    trends_data = await anyio.to_thread.run_sync(get_country_trends)
                    
                    if trends_data and len(trends_data) > 0:
                        trends = [trend["name"] for trend in trends_data[0]["trends"][:max_trends]]
                        trends_result[str(country)] = trends
                        
                        country_duration_ms = round((time.time() - country_start_time) * 1000, 2)
                        logger.debug("Country trends retrieved successfully", extra={
                            "operation": "get_trends",
                            "country": country,
                            "woeid": woeid,
                            "trends_found": len(trends),
                            "country_duration_ms": country_duration_ms
                        })
                    else:
                        trends_result[str(country)] = ["No trends available"]
                        
                except TweepyException as e:
                    custom_exception = handle_tweepy_exception(e, f"get_trends_{country}")
                    trends_result[str(country)] = [f"Error retrieving trends: {custom_exception.message}"]
                    logger.warning("Country trends request failed", extra={
                        "operation": "get_trends",
                        "country": country,
                        "error_type": type(custom_exception).__name__,
                        "country_duration_ms": round((time.time() - country_start_time) * 1000, 2)
                    })
                except Exception as e:
                    trends_result[str(country)] = [f"Error retrieving trends: {str(e)}"]
                    logger.warning("Unexpected error for country trends", extra={
                        "operation": "get_trends",
                        "country": country,
                        "error_type": type(e).__name__,
                        "country_duration_ms": round((time.time() - country_start_time) * 1000, 2)
                    })

            duration_ms = round((time.time() - operation_start) * 1000, 2)
            
            logger.info("Trends retrieval completed", extra={
                "operation": "get_trends",
                "status": "SUCCESS",
                "countries_processed": len(trends_result),
                "duration_ms": duration_ms
            })

            # Format response
            import json
            return json.dumps(trends_result, indent=2)
            
        except BaseMCPException:
            raise
        except Exception as e:
            duration_ms = round((time.time() - operation_start) * 1000, 2)
            logger.error("Unexpected error during trends retrieval", exc_info=True, extra={
                "operation": "get_trends",
                "status": "ERROR",
                "duration_ms": duration_ms,
                "error_type": type(e).__name__
            })
            raise BaseMCPException(f"Trends retrieval failed: {str(e)}")


async def get_twitter_client() -> AsyncTwitterClient:
    """Factory function to create and return configured Twitter client."""
    try:
        from .config import TwitterConfig
        config = TwitterConfig()
        
        logger.info("Creating Twitter client", extra={
            "operation": "get_twitter_client",
            "status": "START"
        })
        
        client = AsyncTwitterClient(config)
        # Initialize the client to test connection
        await client.initialize()
        
        logger.info("Twitter client created successfully", extra={
            "operation": "get_twitter_client",
            "status": "SUCCESS"
        })
        
        return client
        
    except Exception as e:
        logger.error("Failed to create Twitter client", exc_info=True, extra={
            "operation": "get_twitter_client",
            "status": "ERROR",
            "error_type": type(e).__name__
        })
        raise AuthenticationError(f"Failed to create Twitter client: {str(e)}")


# Add the initialize method that was in your original client
    async def initialize(self):
        """
        Initialize and test the Twitter client connection.
        """
        start_time = time.time()
        
        logger.info("Starting Twitter client initialization", extra={
            "operation": "initialize_client",
            "status": "START"
        })
        
        try:
            user = await self.client.get_me()
            
            logger.info("Twitter client initialization completed successfully", extra={
                "operation": "initialize_client",
                "status": "SUCCESS",
                "duration_ms": round((time.time() - start_time) * 1000, 2),
                "authenticated_user": user.data['username']
            })
            
            return self
            
        except TweepyException as e:
            custom_exception = handle_tweepy_exception(e, "initialize_client")
            logger.error("Twitter client initialization failed", extra={
                "operation": "initialize_client",
                "status": "ERROR",
                "duration_ms": round((time.time() - start_time) * 1000, 2),
                "error_type": type(custom_exception).__name__
            })
            raise custom_exception
        except Exception as e:
            logger.error("Twitter client initialization failed", exc_info=True, extra={
                "operation": "initialize_client",
                "status": "ERROR",
                "duration_ms": round((time.time() - start_time) * 1000, 2),
                "system_error": str(e),
                "error_type": type(e).__name__
            })
            raise AuthenticationError(f"Twitter client initialization failed: {str(e)}")
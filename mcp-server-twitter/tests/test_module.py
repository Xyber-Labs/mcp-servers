from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from mcp_server_twitter.twitter.module import AsyncTwitterClient, is_retryable_tweepy_error, get_twitter_client
from tweepy.errors import TweepyException
import requests
import asyncio
from tenacity import retry, stop_after_attempt



# --- Retry Logic Tests (slower, but necessary) ---

@pytest.mark.asyncio
async def test_create_tweet_retries_on_aiohttp_client_error(
    mock_config, mocker, caplog
):
    """
    Test that create_tweet retries on aiohttp.ClientError and eventually succeeds.
    NOTE: This test takes ~3 seconds due to retry delays.
    """
    # Arrange
    twitter_client = AsyncTwitterClient(config=mock_config)

    # Mock the internal tweepy AsyncClient
    mock_async_client = AsyncMock()

    # Simulate failure twice, then success
    mock_async_client.create_tweet.side_effect = [
        aiohttp.ClientError("First failure"),
        aiohttp.ClientError("Second failure"),
        MagicMock(data={"id": "12345"}),  # Successful response
    ]

    # Patch the client instance used by our class
    mocker.patch.object(twitter_client, "client", mock_async_client)

    # Act
    import logging

    caplog.set_level(logging.WARNING)
    tweet_id = await twitter_client.create_tweet(text="Hello world")

    # Assert
    assert tweet_id == "12345"
    assert mock_async_client.create_tweet.call_count == 3

    # We expect 2 WARNING logs from tenacity for the retries
    retry_logs = [rec for rec in caplog.records if rec.levelno == logging.WARNING]
    assert len(retry_logs) == 2
    assert "Retrying" in caplog.text
    assert "ClientError: Second failure" in caplog.text


@pytest.mark.asyncio
async def test_create_tweet_fails_after_max_retries(mock_config, mocker):
    """
    Test that create_tweet fails after the maximum number of retries.
    NOTE: This test takes ~15 seconds due to retry delays.
    """
    # Arrange
    twitter_client = AsyncTwitterClient(config=mock_config)

    mock_async_client = AsyncMock()

    # Simulate persistent failure
    mock_async_client.create_tweet.side_effect = aiohttp.ClientError(
        "Persistent failure"
    )

    mocker.patch.object(twitter_client, "client", mock_async_client)

    # Act & Assert
    with pytest.raises(aiohttp.ClientError):
        await twitter_client.create_tweet(text="This will fail")

    assert mock_async_client.create_tweet.call_count == 5


# --- Fast Functional Tests (bypassing retry logic) ---

@pytest.mark.asyncio
async def test_create_tweet_success_basic(mock_config, mocker):
    """Test basic tweet creation without retry delays."""
    # Arrange
    twitter_client = AsyncTwitterClient(config=mock_config)
    mock_async_client = AsyncMock()
    mock_async_client.create_tweet.return_value = MagicMock(data={"id": "12345"})
    mocker.patch.object(twitter_client, "client", mock_async_client)

    # Act - call the wrapped method directly to bypass retry
    tweet_id = await twitter_client.create_tweet.__wrapped__(twitter_client, text="Hello world")

    # Assert
    assert tweet_id == "12345"
    mock_async_client.create_tweet.assert_awaited_once_with(
        text="Hello world",
        media_ids=None,
        in_reply_to_tweet_id=None,
        quote_tweet_id=None,
    )


@pytest.mark.asyncio
async def test_create_tweet_retries_on_tweepy_5xx_error(mock_config, mocker):
    """
    Test that create_tweet retries on a TweepyException with a 5xx status code.
    NOTE: This test has retry delays.
    """
    # Arrange
    twitter_client = AsyncTwitterClient(config=mock_config)
    mock_async_client = AsyncMock()

    # Mock a 503 Service Unavailable error
    mock_response = MagicMock()
    mock_response.status_code = 503
    tweepy_exception = TweepyException("Service Unavailable")
    tweepy_exception.response = mock_response

    mock_async_client.create_tweet.side_effect = [
        tweepy_exception,
        MagicMock(data={"id": "54321"}),
    ]

    mocker.patch.object(twitter_client, "client", mock_async_client)

    # Act
    tweet_id = await twitter_client.create_tweet(text="Testing 5xx retry")

    # Assert
    assert tweet_id == "54321"
    assert mock_async_client.create_tweet.call_count == 2


@pytest.mark.asyncio
async def test_retweet_retries_and_succeeds(mock_config, mocker, caplog):
    """
    Test that retweet_tweet retries on failure and eventually succeeds.
    NOTE: This test has retry delays.
    """
    # Arrange
    twitter_client = AsyncTwitterClient(config=mock_config)
    mock_async_client = AsyncMock()

    mock_async_client.retweet.side_effect = [
        aiohttp.ClientError("Retweet failed"),
        AsyncMock(),  # Success
    ]
    mocker.patch.object(twitter_client, "client", mock_async_client)

    import logging

    caplog.set_level(logging.WARNING)

    # Act
    result = await twitter_client.retweet_tweet(tweet_id="123")

    # Assert
    assert result == "Successfully retweet post 123"
    assert mock_async_client.retweet.call_count == 2
    assert "Retrying" in caplog.text
    assert "raised ClientError: Retweet failed" in caplog.text


@pytest.mark.asyncio
async def test_retweet_success_fast(mock_config, mocker):
    """Test successful retweet without retry delays."""
    # Arrange
    twitter_client = AsyncTwitterClient(config=mock_config)
    mock_async_client = AsyncMock()
    mock_async_client.retweet.return_value = AsyncMock()
    mocker.patch.object(twitter_client, "client", mock_async_client)

    # Act - call wrapped method directly
    result = await twitter_client.retweet_tweet.__wrapped__(twitter_client, tweet_id="123")

    # Assert
    assert result == "Successfully retweet post 123"
    mock_async_client.retweet.assert_awaited_once_with(tweet_id="123")


@pytest.mark.asyncio
async def test_create_tweet_success_with_media(mock_config, sample_base64_image, mocker):
    """Test creating a tweet with an image successfully."""
    # Arrange
    twitter_client = AsyncTwitterClient(config=mock_config)
    mock_async_client = AsyncMock()
    mock_async_client.create_tweet.return_value = MagicMock(data={"id": "124"})

    # Mock the internal upload method to avoid testing it here
    mocker.patch.object(
        twitter_client, "_upload_media", new_callable=AsyncMock
    ).return_value = MagicMock(media_id="media123")
    mocker.patch.object(twitter_client, "client", mock_async_client)

    # Act - call wrapped method directly for speed
    tweet_id = await twitter_client.create_tweet.__wrapped__(
        twitter_client, text="A tweet with an image", image_content_str=sample_base64_image
    )

    # Assert
    assert tweet_id == "124"
    twitter_client._upload_media.assert_awaited_once_with(sample_base64_image)
    mock_async_client.create_tweet.assert_awaited_once_with(
        text="A tweet with an image",
        media_ids=["media123"],
        in_reply_to_tweet_id=None,
        quote_tweet_id=None,
    )


@pytest.mark.asyncio
async def test_create_tweet_success_with_poll(mock_config, sample_tweet_data, mocker):
    """Test creating a tweet with a poll successfully."""
    # Arrange
    twitter_client = AsyncTwitterClient(config=mock_config)
    mock_async_client = AsyncMock()
    mock_async_client.create_tweet.return_value = MagicMock(data={"id": "125"})
    mocker.patch.object(twitter_client, "client", mock_async_client)

    # Act - call wrapped method directly for speed
    tweet_id = await twitter_client.create_tweet.__wrapped__(
        twitter_client, 
        text="A poll", 
        poll_options=sample_tweet_data["poll_options"][:2],  # Use first 2 options
        poll_duration=sample_tweet_data["poll_duration"]
    )

    # Assert
    assert tweet_id == "125"
    mock_async_client.create_tweet.assert_awaited_once_with(
        text="A poll",
        media_ids=None,
        in_reply_to_tweet_id=None,
        quote_tweet_id=None,
        poll_options=["Yes", "No"],
        poll_duration_minutes=60,
    )


@pytest.mark.asyncio
async def test_create_tweet_fails_on_invalid_poll(mock_config):
    """Test that creating a tweet with invalid poll options raises ValueError immediately."""
    # Arrange
    twitter_client = AsyncTwitterClient(config=mock_config)

    # Act & Assert - call wrapped method directly for speed
    with pytest.raises(ValueError, match="Poll must have 2-4 options"):
        await twitter_client.create_tweet.__wrapped__(
            twitter_client, text="Poll", poll_options=["Only one"]
        )

    with pytest.raises(ValueError, match="Poll duration must be 5-10080 minutes"):
        await twitter_client.create_tweet.__wrapped__(
            twitter_client, text="Poll", poll_options=["Yes", "No"], poll_duration=4
        )


# --- Tests for _upload_media (Sync Retry Logic) ---


@pytest.mark.asyncio
async def test_upload_media_retries_on_requests_exception(mock_config, mocker, caplog):
    """Test that the sync media upload retries on requests.RequestException."""
    # Arrange
    caplog.set_level(logging.WARNING)
    twitter_client = AsyncTwitterClient(config=mock_config)
    mock_media_obj = MagicMock(media_id="media123")
    mock_run_sync = mocker.patch("anyio.to_thread.run_sync", new_callable=AsyncMock)
    mock_run_sync.side_effect = [
        requests.exceptions.RequestException("Sync connection error"),
        mock_media_obj,
    ]

    # Act
    result = await twitter_client._upload_media(image_content_str="base64string")

    # Assert
    assert result.media_id == "media123"
    assert mock_run_sync.call_count == 2
    assert "Retrying" in caplog.text


# --- Tests for get_user_tweets ---


@pytest.mark.asyncio
async def test_get_user_tweets_401_error_logs_details(mock_config, mocker, caplog):
    """Test that a 401 Unauthorized error logs specific helpful messages."""
    # Arrange
    caplog.set_level(logging.ERROR)
    twitter_client = AsyncTwitterClient(config=mock_config)
    mock_async_client = AsyncMock()
    mock_async_client.get_users_tweets.side_effect = Exception("401 Unauthorized")
    mocker.patch.object(twitter_client, "client", mock_async_client)

    # Act & Assert
    with pytest.raises(Exception, match="401 Unauthorized"):
        await twitter_client.get_user_tweets(user_id="user1")

    assert "Twitter API 401 Unauthorized" in caplog.text
    assert "Your app needs Twitter API v2 'tweet.read' scope" in caplog.text


# --- Tests for search_hashtag ---


@pytest.mark.asyncio
async def test_search_hashtag_success_and_adds_hash(mock_config, sample_tweet_data, mocker):
    """Test a successful hashtag search and that '#' is added if missing."""
    # Arrange
    twitter_client = AsyncTwitterClient(config=mock_config)
    mock_async_client = AsyncMock()
    mock_tweet = MagicMock(text="A tweet about python")
    mock_async_client.search_recent_tweets.return_value = MagicMock(data=[mock_tweet])
    mocker.patch.object(twitter_client, "client", mock_async_client)

    # Act
    results = await twitter_client.search_hashtag(hashtag=sample_tweet_data["hashtag"])

    # Assert
    assert results == ["A tweet about python"]
    call_args = mock_async_client.search_recent_tweets.call_args
    assert call_args.kwargs["query"] == "#python"


# NOTE: You will need to import 'aioresponses' at the top of your test file.


@pytest.mark.asyncio
async def test_get_trends_success(mock_config, mock_trends_response):
    """Test successfully fetching trends using aioresponses."""
    # Arrange
    twitter_client = AsyncTwitterClient(config=mock_config)
    egypt_woeid = 23424802

    url = f"https://api.twitter.com/2/trends/by/woeid/{egypt_woeid}?max_trends=50"

    with aioresponses() as m:
        m.get(url, status=200, payload=mock_trends_response)

        # Act
        trends = await twitter_client.get_trends(
            countries=["Egypt"]
        )  # This uses max_trends=50 by default

        # Assert
        assert trends["Egypt"] == ["#TestTrend1", "#TestTrend2", "#TestTrend3"]


@pytest.mark.asyncio
async def test_get_trends_handles_api_error(mock_config, mocker):
    """Test handling of an API error using aioresponses."""
    # Arrange
    twitter_client = AsyncTwitterClient(config=mock_config)
    egypt_woeid = 23424802

    url = f"https://api.twitter.com/2/trends/by/woeid/{egypt_woeid}?max_trends=50"

    with aioresponses() as m:
        m.get(url, status=401, payload={"error": "Unauthorized"})

        # Act
        trends = await twitter_client.get_trends(countries=["Egypt"])

        # Assert
        assert "Error: 401" in trends["Egypt"][0]
        assert "Unauthorized" in trends["Egypt"][0]


# --- Tests for is_retryable_tweepy_error function ---

def test_is_retryable_tweepy_error_non_tweepy_exception():
    """Test that non-TweepyException returns False."""
    # Arrange & Act & Assert
    assert not is_retryable_tweepy_error(ValueError("Some error"))
    assert not is_retryable_tweepy_error(Exception("Generic error"))


def test_is_retryable_tweepy_error_no_response():
    """Test TweepyException without response returns False."""
    # Arrange
    exception = TweepyException("Error without response")
    
    # Act & Assert
    assert not is_retryable_tweepy_error(exception)


def test_is_retryable_tweepy_error_4xx_status():
    """Test TweepyException with 4xx status returns False."""
    # Arrange
    mock_response = MagicMock()
    mock_response.status_code = 400
    exception = TweepyException("Bad Request")
    exception.response = mock_response
    
    # Act & Assert
    assert not is_retryable_tweepy_error(exception)


def test_is_retryable_tweepy_error_5xx_status():
    """Test TweepyException with 5xx status returns True."""
    # Arrange
    mock_response = MagicMock()
    mock_response.status_code = 503
    exception = TweepyException("Service Unavailable")
    exception.response = mock_response
    
    # Act & Assert
    assert is_retryable_tweepy_error(exception)


# --- Tests for follow_user method ---

@pytest.mark.asyncio
async def test_follow_user_success(mock_config, mocker):
    """Test successfully following a user."""
    # Arrange
    twitter_client = AsyncTwitterClient(config=mock_config)
    mock_async_client = AsyncMock()
    mock_async_client.follow_user.return_value = AsyncMock()
    mocker.patch.object(twitter_client, "client", mock_async_client)
    
    # Act
    result = await twitter_client.follow_user("test_user_id")
    
    # Assert
    assert result == "Successfully followed user: test_user_id"
    mock_async_client.follow_user.assert_awaited_once_with(user_id="test_user_id")


@pytest.mark.asyncio
async def test_follow_user_failure(mock_config, mocker, caplog):
    """Test follow_user handles exceptions properly."""
    # Arrange
    caplog.set_level(logging.ERROR)
    twitter_client = AsyncTwitterClient(config=mock_config)
    mock_async_client = AsyncMock()
    mock_async_client.follow_user.side_effect = Exception("Follow failed")
    mocker.patch.object(twitter_client, "client", mock_async_client)
    
    # Act & Assert
    with pytest.raises(Exception, match="Follow failed"):
        await twitter_client.follow_user("test_user_id")
    
    assert "Failed to follow user test_user_id" in caplog.text


# --- Tests for get_user_tweets method ---

@pytest.mark.asyncio
async def test_get_user_tweets_success(mock_config, mock_user_tweets_response, mocker):
    """Test successfully retrieving user tweets."""
    # Arrange
    twitter_client = AsyncTwitterClient(config=mock_config)
    mock_async_client = AsyncMock()
    mock_async_client.get_users_tweets.return_value = mock_user_tweets_response
    mocker.patch.object(twitter_client, "client", mock_async_client)
    
    # Act
    result = await twitter_client.get_user_tweets("test_user", max_results=5)
    
    # Assert
    assert result == mock_user_tweets_response
    mock_async_client.get_users_tweets.assert_awaited_once_with(
        id="test_user",
        max_results=5,
        tweet_fields=["id", "text", "created_at"]
    )


@pytest.mark.asyncio
async def test_get_user_tweets_default_max_results(mock_config, mock_user_tweets_response, mocker):
    """Test get_user_tweets with default max_results."""
    # Arrange
    twitter_client = AsyncTwitterClient(config=mock_config)
    mock_async_client = AsyncMock()
    mock_async_client.get_users_tweets.return_value = mock_user_tweets_response
    mocker.patch.object(twitter_client, "client", mock_async_client)
    
    # Act
    result = await twitter_client.get_user_tweets("test_user")
    
    # Assert
    assert result == mock_user_tweets_response
    mock_async_client.get_users_tweets.assert_awaited_once_with(
        id="test_user",
        max_results=10,
        tweet_fields=["id", "text", "created_at"]
    )


# --- Tests for search_hashtag edge cases ---

@pytest.mark.asyncio
async def test_search_hashtag_no_results(mock_config, mocker):
    """Test search_hashtag when no tweets are found."""
    # Arrange
    twitter_client = AsyncTwitterClient(config=mock_config)
    mock_async_client = AsyncMock()
    mock_async_client.search_recent_tweets.return_value = MagicMock(data=None)
    mocker.patch.object(twitter_client, "client", mock_async_client)
    
    # Act
    result = await twitter_client.search_hashtag("nonexistent")
    
    # Assert
    assert result == []


@pytest.mark.asyncio
async def test_search_hashtag_empty_response(mock_config, mocker):
    """Test search_hashtag when response is None."""
    # Arrange
    twitter_client = AsyncTwitterClient(config=mock_config)
    mock_async_client = AsyncMock()
    mock_async_client.search_recent_tweets.return_value = None
    mocker.patch.object(twitter_client, "client", mock_async_client)
    
    # Act
    result = await twitter_client.search_hashtag("empty")
    
    # Assert
    assert result == []


@pytest.mark.asyncio
async def test_search_hashtag_max_results_clamping(mock_config, mocker):
    """Test that max_results is properly clamped between 10-100."""
    # Arrange
    twitter_client = AsyncTwitterClient(config=mock_config)
    mock_async_client = AsyncMock()
    mock_async_client.search_recent_tweets.return_value = MagicMock(data=[])
    mocker.patch.object(twitter_client, "client", mock_async_client)
    
    # Act
    await twitter_client.search_hashtag("test", max_results=5)  # Below minimum
    call_args_low = mock_async_client.search_recent_tweets.call_args
    
    await twitter_client.search_hashtag("test", max_results=150)  # Above maximum
    call_args_high = mock_async_client.search_recent_tweets.call_args
    
    # Assert
    assert call_args_low.kwargs["max_results"] == 10
    assert call_args_high.kwargs["max_results"] == 100


@pytest.mark.asyncio
async def test_search_hashtag_failure(mock_config, mocker, caplog):
    """Test search_hashtag handles exceptions properly."""
    # Arrange
    caplog.set_level(logging.ERROR)
    twitter_client = AsyncTwitterClient(config=mock_config)
    mock_async_client = AsyncMock()
    mock_async_client.search_recent_tweets.side_effect = Exception("Search failed")
    mocker.patch.object(twitter_client, "client", mock_async_client)
    
    # Act & Assert
    with pytest.raises(Exception, match="Search failed"):
        await twitter_client.search_hashtag("test")
    
    assert "Error searching hashtag #test" in caplog.text


# --- Tests for initialize method ---

@pytest.mark.asyncio
async def test_initialize_success(mock_config, mocker, caplog):
    """Test successful client initialization."""
    # Arrange
    caplog.set_level(logging.INFO)
    twitter_client = AsyncTwitterClient(config=mock_config)
    mock_async_client = AsyncMock()
    mock_user = MagicMock(data={"username": "test_user"})
    mock_async_client.get_me.return_value = mock_user
    mocker.patch.object(twitter_client, "client", mock_async_client)
    
    # Act
    result = await twitter_client.initialize()
    
    # Assert
    assert result == twitter_client
    assert "Successfully authenticated as: test_user" in caplog.text


@pytest.mark.asyncio
async def test_initialize_failure(mock_config, mocker, caplog):
    """Test failed client initialization."""
    # Arrange
    caplog.set_level(logging.ERROR)
    twitter_client = AsyncTwitterClient(config=mock_config)
    mock_async_client = AsyncMock()
    mock_async_client.get_me.side_effect = Exception("Auth failed")
    mocker.patch.object(twitter_client, "client", mock_async_client)
    
    # Act & Assert
    with pytest.raises(Exception, match="Auth failed"):
        await twitter_client.initialize()
    
    assert "Failed to authenticate: Auth failed" in caplog.text


# --- Tests for create_tweet edge cases ---

@pytest.mark.asyncio
async def test_create_tweet_text_truncation(mock_config, mocker):
    """Test that tweet text is truncated to max_tweet_length."""
    # Arrange
    twitter_client = AsyncTwitterClient(config=mock_config)
    mock_async_client = AsyncMock()
    mock_async_client.create_tweet.return_value = MagicMock(data={"id": "123"})
    mocker.patch.object(twitter_client, "client", mock_async_client)
    
    long_text = "A" * 350  # Longer than 280 chars
    
    # Act
    await twitter_client.create_tweet(text=long_text)
    
    # Assert
    call_args = mock_async_client.create_tweet.call_args
    assert len(call_args.kwargs["text"]) == 280
    assert call_args.kwargs["text"] == "A" * 280


@pytest.mark.asyncio
async def test_create_tweet_media_disabled(mock_config, mocker):
    """Test create_tweet when media upload is disabled."""
    # Arrange
    mock_config.media_upload_enabled = False
    twitter_client = AsyncTwitterClient(config=mock_config)
    mock_async_client = AsyncMock()
    mock_async_client.create_tweet.return_value = MagicMock(data={"id": "123"})
    mocker.patch.object(twitter_client, "client", mock_async_client)
    
    # Act
    await twitter_client.create_tweet(text="Test", image_content_str="base64image")
    
    # Assert
    call_args = mock_async_client.create_tweet.call_args
    assert call_args.kwargs["media_ids"] is None


@pytest.mark.asyncio
async def test_create_tweet_with_reply_and_quote(mock_config, mocker):
    """Test create_tweet with reply and quote parameters."""
    # Arrange
    twitter_client = AsyncTwitterClient(config=mock_config)
    mock_async_client = AsyncMock()
    mock_async_client.create_tweet.return_value = MagicMock(data={"id": "123"})
    mocker.patch.object(twitter_client, "client", mock_async_client)
    
    # Act
    await twitter_client.create_tweet(
        text="Test reply",
        in_reply_to_tweet_id="reply123",
        quote_tweet_id="quote456"
    )
    
    # Assert
    call_args = mock_async_client.create_tweet.call_args
    assert call_args.kwargs["in_reply_to_tweet_id"] == "reply123"
    assert call_args.kwargs["quote_tweet_id"] == "quote456"


# --- Tests for get_trends edge cases ---

@pytest.mark.asyncio
async def test_get_trends_unknown_country(mock_config, caplog):
    """Test get_trends with unknown country."""
    # Arrange
    caplog.set_level(logging.ERROR)
    twitter_client = AsyncTwitterClient(config=mock_config)
    
    # Act
    result = await twitter_client.get_trends(["UnknownCountry"])
    
    # Assert
    assert result == {}
    assert "woeid for UnknownCountry not found" in caplog.text


@pytest.mark.asyncio
async def test_get_trends_no_bearer_token(mock_config):
    """Test get_trends raises error when no bearer token is configured."""
    # Arrange
    mock_config.BEARER_TOKEN = None
    twitter_client = AsyncTwitterClient(config=mock_config)
    
    # Act & Assert
    with pytest.raises(ValueError, match="Bearer token not configured"):
        await twitter_client.get_trends(["Egypt"])


@pytest.mark.asyncio
async def test_get_trends_network_exception(mock_config):
    """Test get_trends handles network exceptions."""
    # Arrange
    twitter_client = AsyncTwitterClient(config=mock_config)
    egypt_woeid = 23424802
    url = f"https://api.twitter.com/2/trends/by/woeid/{egypt_woeid}?max_trends=50"
    
    with aioresponses() as m:
        m.get(url, exception=aiohttp.ClientError("Network error"))
        
        # Act
        result = await twitter_client.get_trends(["Egypt"])
        
        # Assert
        assert "Error retrieving trends" in result["Egypt"][0]
        assert "Network error" in result["Egypt"][0]


@pytest.mark.asyncio
async def test_get_trends_multiple_countries(mock_config, sample_tweet_data):
    """Test get_trends with multiple countries."""
    # Arrange
    twitter_client = AsyncTwitterClient(config=mock_config)
    egypt_woeid = 23424802
    france_woeid = 23424819
    
    egypt_url = f"https://api.twitter.com/2/trends/by/woeid/{egypt_woeid}?max_trends=20"
    france_url = f"https://api.twitter.com/2/trends/by/woeid/{france_woeid}?max_trends=20"
    
    with aioresponses() as m:
        m.get(egypt_url, payload={"data": [{"trend_name": "#Cairo"}]})
        m.get(france_url, payload={"data": [{"trend_name": "#Paris"}]})
        
        # Act - use sample countries from fixture
        result = await twitter_client.get_trends(
            sample_tweet_data["countries"][:2], max_trends=20  # Use Egypt, France
        )
        
        # Assert
        assert result["Egypt"] == ["#Cairo"]
        assert result["France"] == ["#Paris"]


# --- Tests for get_twitter_client singleton ---

@pytest.mark.asyncio
async def test_get_twitter_client_singleton():
    """Test that get_twitter_client returns the same instance."""
    # Reset the global client
    import mcp_server_twitter.twitter.module as module
    module._twitter_client = None
    
    with patch('mcp_server_twitter.twitter.config.TwitterConfig') as mock_config_class:
        mock_config = MagicMock()
        mock_config.API_KEY = "test_key"
        mock_config.API_SECRET_KEY = "test_secret"
        mock_config.ACCESS_TOKEN = "test_token"
        mock_config.ACCESS_TOKEN_SECRET = "test_token_secret"
        mock_config.BEARER_TOKEN = "test_bearer"
        mock_config_class.return_value = mock_config
        
        with patch.object(AsyncTwitterClient, 'initialize') as mock_init:
            # We need to create a real client but mock the initialize method
            with patch('tweepy.asynchronous.AsyncClient'), \
                 patch('tweepy.API'), \
                 patch('tweepy.OAuth1UserHandler'):
                mock_client = AsyncTwitterClient(mock_config)
                mock_init.return_value = mock_client
                
                # Act
                client1 = await get_twitter_client()
                client2 = await get_twitter_client()
                
                # Assert
                assert client1 is client2
                mock_init.assert_called_once()


# --- Tests for _upload_media method ---

@pytest.mark.asyncio
async def test_upload_media_success(mock_config, mocker):
    """Test successful media upload."""
    # Arrange
    twitter_client = AsyncTwitterClient(config=mock_config)
    mock_media = MagicMock(media_id="media123")
    mock_run_sync = mocker.patch("anyio.to_thread.run_sync", new_callable=AsyncMock)
    mock_run_sync.return_value = mock_media
    
    # Act
    result = await twitter_client._upload_media("base64string")
    
    # Assert
    assert result.media_id == "media123"
    mock_run_sync.assert_awaited_once()


@pytest.mark.asyncio 
async def test_upload_media_retries_on_tweepy_5xx(mock_config, mocker):
    """Test that media upload retries on TweepyException with 5xx status."""
    # Arrange
    twitter_client = AsyncTwitterClient(config=mock_config)
    mock_response = MagicMock()
    mock_response.status_code = 502
    tweepy_exception = TweepyException("Bad Gateway")
    tweepy_exception.response = mock_response
    
    mock_media = MagicMock(media_id="media123")
    mock_run_sync = mocker.patch("anyio.to_thread.run_sync", new_callable=AsyncMock)
    mock_run_sync.side_effect = [tweepy_exception, mock_media]
    
    # Act
    result = await twitter_client._upload_media("base64string")
    
    # Assert
    assert result.media_id == "media123"
    assert mock_run_sync.call_count == 2

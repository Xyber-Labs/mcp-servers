from pydantic import BaseModel, Field, field_validator


class CreateTweetRequest(BaseModel):
    """Input schema for creating a tweet."""

    text: str = Field(
        ...,
        description="The text content of the tweet. Will be truncated to the configured maximum tweet length if necessary.",
    )
    image_content_str: str | None = Field(
        None,
        description="A Base64-encoded string of image data to attach as media. Optional, pass null for no image. Requires media uploads to be enabled in config.",
    )
    poll_options: list[str] | None = Field(
        None,
        description="A list of 2 to 4 options to include in a poll. Optional, pass null for no poll.",
    )
    poll_duration: int | None = Field(
        None,
        ge=5,
        le=10080,
        description="Duration of the poll in minutes (must be between 5 and 10080). Optional, pass null for no poll.",
    )
    in_reply_to_tweet_id: str | None = Field(
        None,
        description="The ID of an existing tweet to reply to. Optional, pass null for no reply. Note: Your text must include '@username' of the tweet's author.",
    )
    quote_tweet_id: str | None = Field(
        None,
        description="The ID of an existing tweet to quote. Optional, pass null for no quote. The quoted tweet will appear inline, with your text shown above it.",
    )

    @field_validator("poll_options")
    @classmethod
    def check_poll_options_length(cls, v):
        if v is not None and not (2 <= len(v) <= 4):
            raise ValueError("poll_options must contain between 2 and 4 items")
        return v


class GetUserTweetsRequest(BaseModel):
    """Input schema for retrieving recent tweets by user IDs."""

    user_ids: list[str] = Field(
        ..., description="The IDs of the users whose tweets to fetch"
    )
    max_results: int = Field(
        10,
        ge=1,
        le=100,
        description="The maximum number of tweets to return per user (1-100)",
    )


class FollowUserRequest(BaseModel):
    """Input schema for following a Twitter user by user ID."""

    user_id: str = Field(..., description="The ID of the user to follow")


class RetweetTweetRequest(BaseModel):
    """Input schema for retweeting an existing tweet."""

    tweet_id: str = Field(..., description="The ID of the tweet to retweet")


class GetTrendsRequest(BaseModel):
    """Input schema for retrieving trending topics by country."""

    countries: list[str] = Field(..., description="List of countries")
    max_trends: int = Field(
        50,
        ge=1,
        le=50,
        description="Maximum number of trends to return per WOEID (1-50)",
    )


class SearchHashtagRequest(BaseModel):
    """Input schema for searching recent tweets containing a hashtag."""

    hashtag: str = Field(
        ..., description="Hashtag to search for (with or without the leading '#')"
    )
    max_results: int = Field(
        10, ge=10, le=100, description="Maximum number of tweets to return (10-100)"
    )

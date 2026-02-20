class TwitterServiceError(Exception):
    """Base exception for all twitter service related errors."""


class TwitterConfigError(TwitterServiceError):
    """Raised for twitter configuration errors."""


class TwitterApiError(TwitterServiceError):
    """Raised for Apify API errors."""


class TwitterClientError(TwitterServiceError):
    """Raised for unexpected client-side errors."""

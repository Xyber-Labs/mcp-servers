"""
This module should be changed to match the exact error types and handling logic for your service.

Main responsibility: Define a small, typed exception hierarchy for configuration, API, and client errors in the twitter service.
"""


class TwitterServiceError(Exception):
    """Base exception for all twitter service related errors."""


class TwitterConfigError(TwitterServiceError):
    """Raised for twitter configuration errors."""


class TwitterApiError(TwitterServiceError):
    """Raised for Apify API errors."""


class TwitterClientError(TwitterServiceError):
    """Raised for unexpected client-side errors."""


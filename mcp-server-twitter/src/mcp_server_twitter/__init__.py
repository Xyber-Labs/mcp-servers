"""
Twitter MCP Server - FastAPI Implementation

A comprehensive MCP server for Twitter integration with observability,
error handling, and performance monitoring.
"""

from .logging_config import configure_logging

# Configure logging when the module is imported
configure_logging()

# Version information
__version__ = "2.0.0"
__author__ = "MCP Team"
__description__ = "Twitter MCP Server with FastAPI"

# Make key components available at package level
from .exceptions import (
    BaseMCPException,
    ServiceUnavailableError,
    InvalidResponseError,
    AuthenticationError,
    ValidationError,
    RateLimitError,
)

# Import the main application
from .server import app

__all__ = [
    "app",
    "BaseMCPException",
    "ServiceUnavailableError", 
    "InvalidResponseError",
    "AuthenticationError",
    "ValidationError",
    "RateLimitError",
]
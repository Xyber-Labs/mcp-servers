"""
Custom exception classes for the Twitter MCP server.

This module defines a hierarchy of exceptions for better error handling
and user-friendly error messages.
"""


class BaseMCPException(Exception):
    """Base exception for MCP operations"""
    def __init__(self, message: str, error_code: str = "UNKNOWN_ERROR"):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)


class ServiceUnavailableError(BaseMCPException):
    """External service unavailable"""
    def __init__(self, message: str):
        super().__init__(message, "SERVICE_UNAVAILABLE")


class InvalidResponseError(BaseMCPException):
    """Invalid response from external service"""
    def __init__(self, message: str):
        super().__init__(message, "INVALID_RESPONSE")


class AuthenticationError(BaseMCPException):
    """Authentication failed"""
    def __init__(self, message: str):
        super().__init__(message, "AUTHENTICATION_ERROR")


class ValidationError(BaseMCPException):
    """Input validation failed"""
    def __init__(self, message: str):
        super().__init__(message, "VALIDATION_ERROR")


class RateLimitError(BaseMCPException):
    """Rate limit exceeded"""
    def __init__(self, message: str):
        super().__init__(message, "RATE_LIMIT_ERROR")


class NetworkError(BaseMCPException):
    """Network connectivity issues"""
    def __init__(self, message: str):
        super().__init__(message, "NETWORK_ERROR")


class ConfigurationError(BaseMCPException):
    """Configuration or setup issues"""
    def __init__(self, message: str):
        super().__init__(message, "CONFIGURATION_ERROR")
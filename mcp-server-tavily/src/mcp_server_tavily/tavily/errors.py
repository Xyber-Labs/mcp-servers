class TavilyServiceError(Exception):
    pass


class TavilyConfigError(TavilyServiceError):
    pass


class TavilyEmptyQueryError(TavilyServiceError):
    pass


class TavilyApiError(TavilyServiceError):
    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message)
        self.details = details

    def __str__(self) -> str:
        base = super().__str__()
        details_str = f" Details: {self.details}" if self.details else ""
        return f"{base}{details_str}"


class TavilyEmptyResultsError(TavilyServiceError):
    """Raised when Tavily API returns empty results."""
    pass


class TavilyInvalidResponseError(TavilyServiceError):
    """Raised when Tavily API returns an invalid or unexpected response format."""
    pass

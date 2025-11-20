class ArxivServiceError(Exception):
    pass


class ArxivConfigError(ArxivServiceError):
    pass


class ArxivApiError(ArxivServiceError):
    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message)
        self.details = details

    def __str__(self) -> str:
        base = super().__str__()
        details_str = f" Details: {self.details}" if self.details else ""
        return f"{base}{details_str}"


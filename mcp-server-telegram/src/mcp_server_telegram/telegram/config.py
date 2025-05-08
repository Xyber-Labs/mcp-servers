### src/mcp_server_telegram/telegram/config.py

from typing import Optional, Any
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# --- Configuration and Error Classes --- #

class TelegramServiceError(Exception):
    """Base exception for Telegram client errors."""
    pass

class TelegramConfigError(TelegramServiceError):
    """Configuration-related errors for Telegram client."""
    pass

class TelegramApiError(TelegramServiceError):
    """Exception raised for errors during Telegram Bot API calls."""
    def __init__(self, message: str, status_code: Optional[int] = None, details: Optional[Any] = None):
        super().__init__(message)
        self.status_code = status_code
        self.details = details

    def __str__(self) -> str:
        base = super().__str__()
        status_str = f" (HTTP Status: {self.status_code})" if self.status_code else ""
        details_str = f" Details: {self.details}" if self.details else ""
        return f"{base}{status_str}{details_str}"


class TelegramConfig(BaseSettings):
    """
    Configuration for connecting to the Telegram Bot API.
    Reads from environment variables prefixed with TELEGRAM_.
    """
    model_config = SettingsConfigDict(
        env_prefix="TELEGRAM_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    token: str = Field(..., description="The Telegram Bot API token.")
    channel: str = Field(..., description="The Telegram channel ID (e.g., @channelname or chat_id).")
    # Optional: Add other relevant Telegram settings here if needed
    # e.g., parse_mode: str = Field(default="HTML", pattern="^(HTML|MarkdownV2|Markdown)$")
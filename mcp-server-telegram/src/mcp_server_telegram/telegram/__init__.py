### src/mcp_server_telegram/telegram/__init__.py
"""Telegram service module for the MCP server."""

from mcp_server_telegram.telegram.module import _TelegramService, get_telegram_service
from mcp_server_telegram.telegram.config import (
    TelegramConfig,
    TelegramServiceError,
    TelegramApiError,
    TelegramConfigError
)

__all__ = [
    "_TelegramService",
    "get_telegram_service",
    "TelegramConfig",
    "TelegramServiceError",
    "TelegramApiError",
    "TelegramConfigError",
]
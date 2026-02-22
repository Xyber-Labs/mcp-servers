### src/mcp_server_telegram/telegram/__init__.py
"""Telegram service module for the MCP server."""

from mcp_server_telegram.telegram.config import (
    TelegramApiError,
    TelegramConfig,
    TelegramConfigError,
    TelegramServiceError,
)
from mcp_server_telegram.telegram.module import _TelegramService, get_telegram_service

__all__ = [
    "_TelegramService",
    "get_telegram_service",
    "TelegramConfig",
    "TelegramServiceError",
    "TelegramApiError",
    "TelegramConfigError",
]

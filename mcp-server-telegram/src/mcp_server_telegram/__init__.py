### src/mcp_server_telegram/__init__.py
"""MCP Server for Telegram integration."""

from mcp_server_telegram.telegram import (
    TelegramApiError,
    TelegramConfig,
    TelegramConfigError,
    TelegramServiceError,
    _TelegramService,
    get_telegram_service,
)

__all__ = [
    "_TelegramService",
    "get_telegram_service",
    "TelegramConfig",
    "TelegramServiceError",
    "TelegramApiError",
    "TelegramConfigError",
]

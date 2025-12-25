"""
Logging configuration for the MCP YouTube server.
"""

from logging.config import dictConfig
from pathlib import Path

from mcp_server_youtube.config import get_app_settings


def get_logging_config() -> dict:
    """
    Build and return the logging configuration dictionary.

    This is designed to be passed directly to Uvicorn's ``log_config`` parameter
    so that every worker / reload process uses the same configuration.
    """
    settings = get_app_settings()
    logging_level = settings.logging_level

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "standard",
                "level": logging_level,
                "stream": "ext://sys.stdout",
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "standard",
                "filename": "app.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
            },
        },
        "root": {"handlers": ["console"], "level": f"{logging_level}"},
    }


def configure_logging() -> None:
    """
    Configure logging in the *current* process.

    This is useful when running the app without Uvicorn, or in simple scripts.
    When using Uvicorn, prefer passing ``get_logging_config()`` to ``log_config``.
    """
    dictConfig(get_logging_config())


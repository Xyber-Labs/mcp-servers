"""Logging configuration for uvicorn/FastAPI."""

from __future__ import annotations

import logging

from mcp_server_gitparser.config import get_app_settings


def get_logging_config() -> dict:
    """Return a uvicorn-compatible logging config."""
    settings = get_app_settings()
    level = settings.logging_level

    # Keep it simple, but uvicorn expects a dict with these keys.
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "()": "uvicorn.logging.DefaultFormatter",
                "fmt": "%(levelprefix)s %(message)s",
                "use_colors": None,
            },
            "access": {
                "()": "uvicorn.logging.AccessFormatter",
                "fmt": '%(levelprefix)s %(client_addr)s - "%(request_line)s" %(status_code)s',
            },
        },
        "handlers": {
            "default": {
                "formatter": "default",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stderr",
            },
            "access": {
                "formatter": "access",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
            },
        },
        "loggers": {
            "uvicorn": {"handlers": ["default"], "level": level, "propagate": False},
            "uvicorn.error": {"level": level},
            "uvicorn.access": {"handlers": ["access"], "level": level, "propagate": False},
            "mcp_server_gitparser": {"handlers": ["default"], "level": level, "propagate": False},
        },
        "root": {"handlers": ["default"], "level": level},
    }


def configure_root_logging() -> None:
    """Configure Python logging (useful for scripts)."""
    settings = get_app_settings()
    logging.basicConfig(level=getattr(logging, settings.logging_level))


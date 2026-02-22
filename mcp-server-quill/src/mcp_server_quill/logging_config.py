"""
Logging configuration for MCP Quill.
"""

from mcp_server_quill.config import get_app_settings


def get_logging_config() -> dict:
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
        },
        "loggers": {
            "docket": {"level": "WARNING"},
            "fakeredis": {"level": "WARNING"},
            "httpx": {"level": "WARNING"},
            "httpcore": {"level": "WARNING"},
        },
        "root": {"handlers": ["console"], "level": f"{logging_level}"},
    }

from logging.config import dictConfig

from mcp_server_arxiv.config import get_app_settings


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
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "standard",
                "filename": "app.log",
                "maxBytes": 10485760,
                "backupCount": 5,
            },
        },
        "root": {"handlers": ["console"], "level": f"{logging_level}"},
    }


def configure_logging() -> None:
    dictConfig(get_logging_config())

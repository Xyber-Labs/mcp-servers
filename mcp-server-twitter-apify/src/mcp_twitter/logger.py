from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


def _project_root() -> Path:
    # <repo>/src/mcp_twitter/logger.py -> repo root is 2 levels up.
    return Path(__file__).resolve().parents[2]


def get_logger(name: str = "mcp_twitter") -> logging.Logger:
    """
    Create (or return) a configured logger.

    Avoids adding duplicate handlers on repeated imports.
    """
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    logger = logging.getLogger(name)
    logger.setLevel(level)

    if getattr(logger, "_mcp_twitter_configured", False):
        return logger

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(logging.Formatter(LOG_FORMAT))

    log_dir = _project_root() / "logs"
    log_dir.mkdir(exist_ok=True)
    file_handler = logging.FileHandler(log_dir / f"{name}.log", encoding="utf-8")
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT))

    logger.addHandler(stream_handler)
    logger.addHandler(file_handler)
    logger.propagate = False

    setattr(logger, "_mcp_twitter_configured", True)
    return logger


logger = get_logger()

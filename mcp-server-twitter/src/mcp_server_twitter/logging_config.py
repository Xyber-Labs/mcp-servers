# This template file mostly will stay the same for all MCP servers
# You can edit it to change logging configuration
# Or add/edit handlers as needed
import os
import logging
from logging.config import dictConfig

"""Configures structured logging for the application."""
logging_level = os.getenv("LOG_LEVEL", "INFO")

# Custom formatter to show extra fields (for file logging)
class StructuredFormatter(logging.Formatter):
    """Shows extra fields in a readable format"""
    
    def format(self, record):
        # Format the basic message
        base_msg = super().format(record)
        
        # Add extra fields if they exist
        extra_fields = []
        for key, value in record.__dict__.items():
            # Skip standard logging fields
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                          'filename', 'module', 'lineno', 'funcName', 'created', 'msecs', 
                          'relativeCreated', 'thread', 'threadName', 'processName', 'process',
                          'message', 'exc_info', 'exc_text', 'stack_info', 'asctime']:
                extra_fields.append(f"{key}={value}")
        
        if extra_fields:
            return f"{base_msg} | {' '.join(extra_fields)}"
        return base_msg

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "structured": {
            "()": StructuredFormatter,
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",  # Simple format for console
            "level": logging_level,
            "stream": "ext://sys.stdout",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "structured",  # Structured format for file
            "level": "DEBUG",
            "filename": "app.log",  # Changed back to app.log as requested
            "maxBytes": 10485760,
            "backupCount": 5,
            "encoding": "utf-8",
        },
    },
    "root": {
        "handlers": ["console", "file"], 
        "level": "DEBUG",  # Root captures everything, handlers filter
    },
}

def configure_logging():
    """Apply logging configuration."""
    # Ensure log directory exists
    os.makedirs(".", exist_ok=True)
    
    dictConfig(LOGGING_CONFIG)
    
    # Test the structured logging
    logger = logging.getLogger(__name__)
    logger.info("Structured logging configured", extra={
        "operation": "logging_setup",
        "status": "SUCCESS", 
        "log_level": logging_level
    })
    
    if logging_level == "DEBUG":
        logger.debug("Debug mode enabled", extra={
            "operation": "debug_test",
            "status": "ENABLED"
        })
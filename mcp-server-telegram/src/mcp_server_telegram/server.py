### src/mcp_server_telegram/server.py
import logging
from enum import StrEnum
from typing import AsyncIterator, List, Dict, Any, Literal
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError

from mcp.server import Server
from mcp.types import Tool, TextContent
from pydantic import BaseModel, Field, ValidationError

from mcp_server_telegram.telegram import (
    _TelegramService,
    get_telegram_service,
    TelegramServiceError,
    TelegramConfigError,
)

logger = logging.getLogger(__name__)

# --- Tool Constants & Enums --- #
class TelegramToolNames(StrEnum):
    """Enum for Telegram MCP tool names."""
    POST_MESSAGE = "post_to_telegram"

# --- Tool Input/Output Schemas --- #
class TelegramPostRequest(BaseModel):
    """Input schema for the post_to_telegram tool."""
    message: str = Field(..., description="The text message content to post to the Telegram channel.")

# --- Lifespan Management --- #
@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[dict[str, Any]]:
    """Manage server startup/shutdown. Initializes the Telegram service."""
    logger.info("Lifespan: Initializing services...")
    
    try:
        # Initialize services
        telegram_service: _TelegramService = get_telegram_service()
        
        logger.info("Lifespan: Services initialized successfully")
        yield {"telegram_service": telegram_service}
    
    except TelegramConfigError as init_err:
        logger.error(f"FATAL: Lifespan initialization failed: {init_err}", exc_info=True)
        raise init_err
    
    except Exception as startup_err:
        logger.error(f"FATAL: Unexpected error during lifespan initialization: {startup_err}", exc_info=True)
        raise startup_err
    
    finally:
        logger.info("Lifespan: Shutdown cleanup completed")

# --- MCP Server Initialization --- #
mcp_server = FastMCP(
    name="telegram",
    description="Post messages to a pre-configured Telegram channel",
    lifespan=app_lifespan
)

# --- Tool Definitions --- #
@mcp_server.tool()
async def post_to_telegram(
    ctx: Context,
    message: str, 
) -> str:
    """Posts a given message to a pre-configured Telegram channel."""
    telegram_service = ctx.request_context.lifespan_context["telegram_service"]

    try:
        success: bool = await telegram_service.send_message(message)
        
        if success:
            logger.info("Message successfully posted to the Telegram channel")
            return "Message successfully posted to the Telegram channel"
        else:
            logger.warning("Failed to post message to the Telegram channel")
            raise ToolError("Failed to post message to the Telegram channel")
    
    except TelegramServiceError as service_err:
        logger.error(f"Service error during message posting: {service_err}")
        raise ToolError(f"Telegram service error: {service_err}") from service_err
    
    except Exception as e:
        logger.error(f"Unexpected error during message posting: {e}", exc_info=True)
        raise ToolError("An unexpected error occurred during message posting.") from e

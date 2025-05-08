### src/mcp_server_telegram/server.py
import logging
from enum import StrEnum
from typing import AsyncIterator, List, Dict, Any
from contextlib import asynccontextmanager

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

# --- MCP Server Initialization --- #
@asynccontextmanager
async def server_lifespan(server_instance: Server) -> AsyncIterator[Dict[str, Any]]:
    """
    Manage MCP server startup/shutdown. Initializes the Telegram service.
    """
    logger.info("MCP Lifespan: Initializing Telegram service...")
    context = {}
    try:
        # Attempt to get the service. If config is invalid, this will raise TelegramConfigError.
        telegram_service = get_telegram_service()
        context["telegram_service"] = telegram_service
        logger.info("MCP Lifespan: Telegram service initialized successfully.")
        yield context
    except TelegramConfigError as e:
        logger.error(f"FATAL: MCP Lifespan: Telegram service initialization failed due to config error: {e}", exc_info=True)
        yield context 
    except Exception as e:
        logger.error(f"FATAL: MCP Lifespan: Unexpected error during Telegram service initialization: {e}", exc_info=True)
        yield context
    finally:
        logger.info("MCP Lifespan: Shutdown (Telegram).")

server = Server("telegram-mcp-server", lifespan=server_lifespan)

# --- Tool Definitions --- #

@server.list_tools()
async def list_tools() -> list[Tool]:
    """Lists the tools available in this MCP server."""
    logger.debug("Listing available Telegram tools.")
    
    return [
        Tool(
            name=TelegramToolNames.POST_MESSAGE.value,
            description="Posts a given message to a pre-configured Telegram channel.",
            inputSchema=TelegramPostRequest.model_json_schema(),
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handles incoming tool calls for the Telegram MCP server."""
    logger.info(f"Received call_tool request for '{name}' with args: {arguments}")

    # Retrieve the service instance from request_context's lifespan_context
    try:
        telegram_service: _TelegramService = server.request_context.lifespan_context["telegram_service"]
    except KeyError:
        error_msg = (
            "Server Lifecycle Error: Telegram service not found in request context. "
            "This likely means the service failed to initialize during server startup. "
            "Check server logs for 'MCP Lifespan' errors related to Telegram service initialization."
        )
        logger.error(error_msg)
        return [TextContent(type="text", text=error_msg)]


    # --- Tool Business Logic --- #
    if name == TelegramToolNames.POST_MESSAGE.value:
        try:
            # 1. Validate Input
            request_model = TelegramPostRequest(**arguments)
            
            # 2. Execute Core Logic using the service
            success: bool = await telegram_service.send_message(request_model.message)
            
            # 3. Format and return result
            if success:
                response_text = "Message successfully posted to the Telegram channel."
                logger.info(response_text)
            else:
                response_text = "Failed to post message to the Telegram channel. Check server logs for details."
                logger.warning(response_text) # The service logs more specific errors
            
            return [TextContent(type="text", text=response_text)]

        except ValidationError as ve:
            error_msg = f"Invalid arguments for tool '{name}': {ve}"
            logger.warning(error_msg)
            return [TextContent(type="text", text=error_msg)]
        
        except TelegramServiceError as service_err:
            error_msg = f"Telegram service error processing tool '{name}': {service_err}"
            logger.error(error_msg, exc_info=True)
            return [TextContent(type="text", text=error_msg)]

        except Exception as e:
            error_msg = f"An unexpected internal error occurred processing tool '{name}'. Details: {e}"
            logger.error(error_msg, exc_info=True)
            return [TextContent(type="text", text=error_msg)]
    
    # --- Handle Unknown Tool --- #
    else:
        logger.warning(f"Received call for unknown tool: {name}")
        return [TextContent(type="text", text=f"Unknown tool: {name}")]
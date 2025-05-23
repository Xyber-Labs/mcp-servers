"""
MCP server implementation for Qdrant vector database.
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from enum import StrEnum
from typing import Any, Literal
from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError
    
from mcp.server import Server
from mcp.types import TextContent, Tool
from pydantic import BaseModel, Field, ValidationError

from mcp_server_qdrant.qdrant import (
    Entry, 
    QdrantConnector, 
    get_qdrant_connector
)

logger = logging.getLogger(__name__)

# --- Tool Input/Output Schemas --- #

class QdrantStoreRequest(BaseModel):
    """Input schema for the qdrant-store tool."""
    information: str = Field(..., description="The information to store.")
    collection_name: str = Field(..., description="The name of the collection to store the information in.")
    metadata: dict | None = Field(None, description="JSON metadata to store with the information, optional.")

class QdrantFindRequest(BaseModel):
    """Input schema for the qdrant-find tool."""
    query: str = Field(..., description="The query to use for the search.")
    collection_name: str = Field(..., description="The name of the collection to search in.")
    search_limit: int = Field(10, description="The maximum number of results to return.")

# --- Tool Name Enums --- #

class ToolNames(StrEnum):
    QDRANT_STORE = "qdrant-store"
    QDRANT_FIND = "qdrant-find"


# --- Lifespan Management for MCP Server --- #

@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[dict[str, Any]]:
    """Manage server startup/shutdown. Initializes Qdrant services."""
    logger.info("Lifespan: Initializing services...")
    
    try:
        # Initialize services
        qdrant_connector: QdrantConnector = get_qdrant_connector()
        
        logger.info("Lifespan: Services initialized successfully")
        yield {"qdrant_connector": qdrant_connector}
    
    except Exception as init_err:
        logger.error(f"FATAL: Lifespan initialization failed: {init_err}", exc_info=True)
        raise init_err
    
    finally:
        logger.info("Lifespan: Shutdown cleanup completed")

# --- MCP Server Initialization --- #
mcp_server = FastMCP(
    name="qdrant",
    description="Store and retrieve information using Qdrant vector database",
    lifespan=app_lifespan
)

# --- Tool Definitions --- #

@mcp_server.tool()
async def qdrant_store(
    ctx: Context,
    information: str,  # The information to store
    collection_name: str,  # The name of the collection to store the information in
    metadata: dict | None = None,  # JSON metadata to store with the information, optional
) -> str:
    """Keep the memory for later use, when you are asked to remember something."""
    qdrant_connector = ctx.request_context.lifespan_context["qdrant_connector"]

    try:
        # Execute core logic
        entry = Entry(content=information, metadata=metadata)
        await qdrant_connector.store(entry, collection_name=collection_name)
        
        logger.info(f"Successfully stored information in collection {collection_name}")
        return f"Remembered: {information} in collection {collection_name}"
    
    except Exception as e:
        logger.error(f"Error storing information: {e}", exc_info=True)
        raise ToolError(f"Error storing information: {e}") from e

@mcp_server.tool()
async def qdrant_find(
    ctx: Context,
    query: str,  # The query to use for the search
    collection_name: str,  # The name of the collection to search in
    search_limit: int = 10,  # The maximum number of results to return
) -> str:
    """Look up memories in Qdrant. Use this tool when you need to find memories by their content, access memories for further analysis, or get some personal information about the user."""
    qdrant_connector = ctx.request_context.lifespan_context["qdrant_connector"]

    try:
        # Execute core logic
        entries = await qdrant_connector.search(
            query,
            collection_name=collection_name,
            limit=search_limit
        )
        
        # Format response
        if not entries:
            logger.info(f"No information found for the query '{query}'")
            return f"No information found for the query '{query}'"
        
        content = [f"Results for the query '{query}'"]
        for entry in entries:
            content.append(str(entry))
        
        logger.info(f"Successfully searched Qdrant with {len(entries)} results")
        return "\n".join(content)
    
    except Exception as e:
        logger.error(f"Error searching Qdrant: {e}", exc_info=True)
        raise ToolError(f"Error searching Qdrant: {e}") from e

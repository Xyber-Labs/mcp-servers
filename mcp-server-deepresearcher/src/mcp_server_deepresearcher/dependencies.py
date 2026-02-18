"""
FastAPI dependencies for accessing shared resources from app state.

Main responsibility: Provide a single place to access all service clients used by the application.
Lifecycle is managed externally (in lifespan) following dependency injection principles.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from langchain_core.language_models import BaseChatModel

from mcp_server_deepresearcher.deepresearcher.state import ToolDescription

if TYPE_CHECKING:
    from mcp_server_deepresearcher.db.database import Database
    from xyber_sdk.mcp_client import McpClient

logger = logging.getLogger(__name__)


class DependencyContainer:
    """
    Centralized container for all application dependencies.

    Usage:
        # In app.py lifespan:
        DependencyContainer.create(
            llm=llm,
            llm_thinking=llm_thinking,
            mcp_client=mcp_client,
            tools_description=tools_description,
            database=db,  # Can be None if not configured
        )
        yield
        DependencyContainer.clear()

        # In route handlers via Depends():
        @router.get("/reports")
        async def get_reports(db: Database | None = Depends(get_database)):
            ...
    """

    _llm: BaseChatModel | None = None
    _llm_thinking: BaseChatModel | None = None
    _mcp_client: McpClient | None = None
    _tools_description: list[ToolDescription] = []
    _database: Database | None = None

    @classmethod
    def create(
        cls,
        *,
        llm: BaseChatModel,
        llm_thinking: BaseChatModel,
        mcp_client: McpClient,
        tools_description: list[ToolDescription],
        database: Database | None = None,
    ) -> None:
        """Store all dependencies (call from lifespan startup)."""
        cls._llm = llm
        cls._llm_thinking = llm_thinking
        cls._mcp_client = mcp_client
        cls._tools_description = tools_description
        cls._database = database

    @classmethod
    def clear(cls) -> None:
        """Clear all dependencies (call from lifespan shutdown)."""
        cls._llm = None
        cls._llm_thinking = None
        cls._mcp_client = None
        cls._tools_description = []
        cls._database = None

    @classmethod
    async def get_mcp_tools(cls) -> list:
        """Get MCP tools from the client (fetches on-demand)."""
        if cls._mcp_client is None:
            logger.warning("MCP client not initialized")
            return []
        try:
            return await cls._mcp_client.get_all_tools()
        except Exception as e:
            logger.error(f"Failed to get MCP tools: {e}")
            return []

    @classmethod
    def get_research_resources(cls) -> dict:
        """Get research resources for route handlers."""
        if cls._llm is None:
            raise RuntimeError(
                "DependencyContainer not created. Call DependencyContainer.create() first."
            )
        return {
            "llm": cls._llm,
            "llm_thinking": cls._llm_thinking,
            "mcp_client": cls._mcp_client,
            "tools_description": cls._tools_description,
        }

    @classmethod
    def get_database(cls) -> Database | None:
        """Get the Database instance (may be None if not configured)."""
        return cls._database


get_research_resources = DependencyContainer.get_research_resources
get_database = DependencyContainer.get_database

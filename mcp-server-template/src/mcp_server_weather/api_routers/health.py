"""
Free REST-only healthcheck example.

This module is intended as a lightweight template: many MCP servers will keep a
similar health endpoint, but you can freely adjust the path, payload, or status
fields to match your infrastructure and monitoring requirements.
"""

import logging

from fastapi import APIRouter

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/health",
    tags=["Admin"],
    # IMPORTANT: The `operation_id` provides a unique, stable identifier for this
    # endpoint. While optional in FastAPI, it is CRUCIAL for this template as it's
    # used by the pricing system and other integrations. Always define one.
    operation_id="get_server_health",
)
async def get_server_health():
    """
    Returns the operational status of the server.

    This endpoint is useful for health checks, load balancers, and monitoring
    systems. It is not exposed to MCP because AI agents don't need to check
    server health.
    """
    logger.info("Health check endpoint was called")
    return {
        "status": "ok",
        "service": "mcp-server-weather",
    }

"""
REST-only healthcheck endpoint for monitoring and load balancer probes.
"""

import logging

from fastapi import APIRouter

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/health",
    tags=["Admin"],
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
        "service": "mcp-server-deep-researcher",
    }


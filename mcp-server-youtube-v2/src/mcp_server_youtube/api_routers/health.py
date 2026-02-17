"""
Health check endpoint for monitoring and load balancer probes.
"""

import logging

from fastapi import APIRouter

from mcp_server_youtube.schemas import HealthCheckResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/health",
    tags=["Admin"],
    operation_id="get_server_health",
    response_model=HealthCheckResponse,
)
async def get_server_health() -> HealthCheckResponse:
    """
    Returns the operational status of the server.

    This endpoint is useful for health checks, load balancers, and monitoring
    systems. It is not exposed to MCP because AI agents don't need to check
    server health.
    """
    logger.info("Health check endpoint was called")
    return HealthCheckResponse(
        status="healthy",
        service="mcp_youtube_api",
    )

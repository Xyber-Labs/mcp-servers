import logging

from fastapi import APIRouter

from mcp_server_arxiv.schemas import HealthCheckResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/health",
    tags=["Admin"],
    operation_id="get_server_health",
    response_model=HealthCheckResponse,
)
async def get_server_health() -> HealthCheckResponse:
    logger.info("Health check endpoint was called")
    return HealthCheckResponse(
        status="ok",
        service="mcp-server-arxiv",
    )

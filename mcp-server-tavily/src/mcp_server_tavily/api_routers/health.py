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
    logger.info("Health check endpoint was called")
    return {
        "status": "ok",
        "service": "mcp-server-tavily",
    }


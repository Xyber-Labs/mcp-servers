from fastapi import APIRouter

from mcp_server_quill.schemas import HealthCheckResponse

router = APIRouter(tags=["Health"])


@router.get("/health", summary="Health Check", response_model=HealthCheckResponse)
async def health_check():
    """
    Health check endpoint.

    Returns:
        dict: Status indicator showing API is healthy

    """
    return {"status": "healthy"}

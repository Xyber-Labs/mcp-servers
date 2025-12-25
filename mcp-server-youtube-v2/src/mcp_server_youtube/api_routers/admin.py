"""
Admin endpoints for administrative operations.
"""

import logging

from fastapi import APIRouter

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/admin/logs",
    tags=["Admin"],
    operation_id="get_admin_logs",
)
async def get_admin_logs():
    """
    Retrieves server logs for administrative purposes.

    This is a premium endpoint that requires x402 payment. It demonstrates
    how to monetize sensitive or resource-intensive REST endpoints while
    keeping them unavailable to AI agents.
    """
    logger.info("Paid endpoint '/admin/logs' was accessed successfully.")
    return {
        "logs": [
            {
                "timestamp": "2025-01-01T00:00:00Z",
                "level": "INFO",
                "message": "Server started",
            },
            {
                "timestamp": "2025-01-01T00:01:00Z",
                "level": "INFO",
                "message": "YouTube service initialized",
            },
        ]
    }


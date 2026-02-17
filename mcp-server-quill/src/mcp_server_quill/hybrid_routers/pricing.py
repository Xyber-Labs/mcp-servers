import logging

import yaml
from fastapi import APIRouter, status

from mcp_server_quill.schemas import PricingResponse
from mcp_server_quill.x402_integration import get_x402_settings

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/pricing", status_code=status.HTTP_200_OK, response_model=PricingResponse)
async def get_pricing() -> dict:
    """Get tool pricing configuration."""
    settings = get_x402_settings()
    try:
        if not settings.pricing_config_path.exists():
            return {
                "pricing": {},
                "message": "No pricing configured; all endpoints are free to use",
            }

        with open(settings.pricing_config_path) as f:
            pricing_data = yaml.safe_load(f) or {}

        return {"pricing": pricing_data}
    except Exception as e:
        logger.error(f"Error reading pricing config: {e}")
        raise

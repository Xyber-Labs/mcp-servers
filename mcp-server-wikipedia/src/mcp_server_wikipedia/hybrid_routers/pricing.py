import logging

import yaml
from fastapi import APIRouter, status

from mcp_server_wikipedia.schemas import PricingResponse
from mcp_server_wikipedia.x402_integration.config import get_x402_settings

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/pricing",
    status_code=status.HTTP_200_OK,
    operation_id="wikipedia_get_pricing",
    tags=["Pricing"],
    response_model=PricingResponse,
)
async def get_pricing() -> PricingResponse:
    """Get tool pricing configuration."""
    settings = get_x402_settings()
    try:
        if not settings.pricing_config_path.exists():
            return PricingResponse(
                pricing={},
                message="No pricing configured; all endpoints are free to use",
            )

        with open(settings.pricing_config_path) as f:
            pricing_data = yaml.safe_load(f) or {}

        return PricingResponse(pricing=pricing_data)
    except Exception as e:
        logger.error(f"Error reading pricing config: {e}")
        raise

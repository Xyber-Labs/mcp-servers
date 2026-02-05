import logging

from fastapi import APIRouter, Request
from fastmcp.exceptions import ToolError

from mcp_server_aave.aave import AaveClient, AaveError

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/available-networks",
    tags=["Aave"],
    operation_id="aave_get_available_networks",
)
async def get_available_networks(request: Request) -> list[str]:
    """Return a list of supported Aave networks.

    The list is sourced from the upstream Aave GraphQL API and may vary over time.
    """
    aave_client: AaveClient = request.app.state.aave_client
    try:
        return await aave_client.get_available_networks()
    except AaveError as e:
        logger.error(f"Failed to get available networks: {e}", exc_info=True)
        raise ToolError("Failed to retrieve available networks from Aave API.") from e

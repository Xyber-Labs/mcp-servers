import logging
from typing import Annotated

from fastapi import APIRouter, Request
from fastmcp.exceptions import ToolError
from pydantic import BaseModel, Field

from mcp_server_aave.aave import AaveApiError, AaveClient, AaveClientError
from mcp_server_aave.schemas import (
    AAVE_ASSETS,
    AAVE_NETWORKS,
    ComprehensiveAaveData,
    NetworkAaveData,
)

logger = logging.getLogger(__name__)
router = APIRouter()


class ComprehensiveAaveDataRequest(BaseModel):
    """Request model for comprehensive Aave data."""

    networks: Annotated[
        list[AAVE_NETWORKS] | None,
        Field(
            default=None,
            description="Optional: A list of blockchain networks to query. If not provided, data for all networks will be returned.",
        ),
    ] = None
    asset_symbols: Annotated[
        list[AAVE_ASSETS] | None,
        Field(
            default=None,
            description="Optional: A list of token symbols to get detailed data for.",
        ),
    ] = None


@router.post(
    "/comprehensive-aave-data",
    tags=["Aave"],
    operation_id="aave_get_comprehensive_data",
)
async def get_comprehensive_aave_data(
    request_data: ComprehensiveAaveDataRequest,
    request: Request,
) -> ComprehensiveAaveData:
    """Fetch a simplified Aave view for agents.

    Returns a list of networks, each containing:
      - an aggregated overview (liquidity, debt, utilization)
      - a list of reserve summaries (APY, totals)

    Optional filters:
      - networks: restricts to a list of networks (e.g. ["ethereum", "polygon"])
      - asset_symbols: restricts reserves to the specified token symbols
    """
    aave_client: AaveClient = request.app.state.aave_client

    try:
        networks_to_query = (
            request_data.networks
            if request_data.networks
            else await aave_client.get_available_networks()
        )
        chain_id_map = {
            "ethereum": 1,
            "polygon": 137,
            "avalanche": 43114,
            "arbitrum": 42161,
            "optimism": 10,
        }
        chain_ids = [
            chain_id_map.get(n.lower())
            for n in networks_to_query
            if chain_id_map.get(n.lower())
        ]

        markets = await aave_client.get_markets_data(chain_ids=chain_ids)

        all_network_data = []

        for market in markets:
            # Optional filtering by network name argument
            if request_data.networks and market.chain.name.lower() not in [
                n.lower() for n in request_data.networks
            ]:
                continue

            network_data = NetworkAaveData._from_pool_data(
                pool=market,
                asset_symbols=request_data.asset_symbols,
            )

            # If asset filter was applied and this market has no reserves, skip
            if request_data.asset_symbols and not network_data.reserves:
                continue

            all_network_data.append(network_data)

        return ComprehensiveAaveData(data=all_network_data)

    except AaveApiError as api_err:
        logger.error(f"AAVE API error: {api_err}", exc_info=True)
        raise ToolError(f"AAVE API error: {api_err}") from api_err

    except AaveClientError as client_err:
        logger.error(f"AAVE client error: {client_err}", exc_info=True)
        raise ToolError(f"AAVE client error: {client_err}") from client_err

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise ToolError("An unexpected error occurred.") from e

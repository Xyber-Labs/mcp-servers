import logging

from fastapi import APIRouter, HTTPException, Path, Query

from mcp_server_quill.dependencies import SearchClientDep
from mcp_server_quill.schemas import TokenSearchResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Search"])


@router.get(
    "/search/{query}",
    operation_id="search_token_address",
    summary="Search for Token Address",
    description="""
    Search for a token's contract address by its name or symbol.

    This endpoint uses DexScreener to find token addresses across multiple blockchains.
    It's useful when you only know the token's name or symbol and need its contract address.
    """,
    response_description="Token address information including contract address, name, symbol, and chain.",
    response_model=TokenSearchResponse,
)
async def search_token_address(
    search_client: SearchClientDep,
    query: str = Path(
        ...,
        description="Token name or symbol to search for (e.g., 'WETH', 'CAKE', 'RAY', 'PEPE')",
        example="WETH",
    ),
    chain: str | None = Query(
        None,
        description="""
        Optional chain filter to narrow down search results.

        **Supported chains:**
        - `ethereum` or `eth` - Ethereum Mainnet
        - `bsc` - Binance Smart Chain
        - `solana` or `sol` - Solana
        - `polygon` - Polygon
        - `arbitrum` - Arbitrum
        - `avalanche` - Avalanche

        If not provided, returns the first match across all chains.
        """,
        example="ethereum",
    ),
):
    try:
        result = await search_client.search_token(query, chain_id=chain)
        if not result:
            chain_info = f" on chain '{chain}'" if chain else ""
            raise HTTPException(
                status_code=404, detail=f"Token '{query}' not found{chain_info}"
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error searching token")
        raise HTTPException(status_code=500, detail="Internal server error") from e

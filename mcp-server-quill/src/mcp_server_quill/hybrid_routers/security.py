import logging

from fastapi import APIRouter, HTTPException, Path, Query

from mcp_server_quill.dependencies import QuillClientDep, SearchClientDep
from mcp_server_quill.schemas import TokenSecurityResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/evm/{query}",
    operation_id="get_evm_token_info",
    tags=["EVM Security"],
    summary="Get EVM Token Security Analysis",
    description="""
    Get comprehensive security analysis for an EVM-compatible token.

    This endpoint performs a two-step process:
    1. **Searches** for the token's contract address using the token name/symbol
    2. **Analyzes** the token's security using QuillCheck API
    """,
    response_model=TokenSecurityResponse,
)
async def get_evm_token_info(
    quill_client: QuillClientDep,
    search_client: SearchClientDep,
    query: str = Path(
        ...,
        description="Token name or symbol to analyze (e.g., 'WETH', 'CAKE', 'USDC', 'DAI')",
        example="WETH",
    ),
    quill_chain_id: str = Query(
        "1",
        description="""
        Quill Chain ID - Numeric identifier for the blockchain network.
        
        **Common Chain IDs:**
        - `1` - Ethereum Mainnet (default)
        - `56` - BSC (Binance Smart Chain)
        - `137` - Polygon
        - `42161` - Arbitrum
        - `10` - Optimism
        - `43114` - Avalanche C-Chain
        """,
        example="1",
    ),
):
    # 1. Map quill_chain_id to dexscreener chain name for better search
    chain_map = {
        "1": "ethereum",
        "56": "bsc",
        "137": "polygon",
        "42161": "arbitrum",
        "10": "optimism",
        "43114": "avalanche",
    }
    dex_chain = chain_map.get(quill_chain_id)

    if not dex_chain:
        raise HTTPException(
            status_code=400, detail=f"Unsupported chain ID: {quill_chain_id}"
        )

    # 2. Get address using search client directly
    search_result = await search_client.search_token(query, chain_id=dex_chain)
    if not search_result:
        chain_info = f" on chain '{dex_chain}'" if dex_chain else ""
        raise HTTPException(
            status_code=404, detail=f"Token '{query}' not found{chain_info}"
        )

    address = search_result["address"]

    # 3. Get Quill info
    try:
        data = await quill_client.get_token_info(address, chain_id=quill_chain_id)
        return {"search_result": search_result, "quill_data": data}
    except Exception as e:
        logger.exception("Quill API error")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get(
    "/solana/{query}",
    operation_id="get_solana_token_info",
    tags=["Solana Security"],
    summary="Get Solana Token Security Analysis",
    description="""
    Get comprehensive security analysis for a Solana token.

    This endpoint performs a two-step process:
    1. **Searches** for the token's mint address using the token name/symbol
    2. **Analyzes** the token's security using QuillCheck API
    """,
    response_model=TokenSecurityResponse,
)
async def get_solana_token_info(
    quill_client: QuillClientDep,
    search_client: SearchClientDep,
    query: str = Path(
        ...,
        description="Token name or symbol to analyze (e.g., 'RAY', 'BONK', 'USDC', 'SOL')",
        example="RAY",
    ),
):
    # 1. Get address using search client directly
    search_result = await search_client.search_token(query, chain_id="solana")
    if not search_result:
        raise HTTPException(
            status_code=404, detail=f"Token '{query}' not found on Solana"
        )

    address = search_result["address"]

    # 2. Get Quill info
    try:
        data = await quill_client.get_solana_token_info(address)
        return {"search_result": search_result, "quill_data": data}
    except Exception as e:
        logger.exception("Quill API error")
        raise HTTPException(status_code=500, detail="Internal server error") from e

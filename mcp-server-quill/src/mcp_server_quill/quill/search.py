import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class TokenSearchAPI:
    """Class to search for token addresses using DexScreener API."""

    def __init__(self, base_url: str = "https://api.dexscreener.com/latest/dex/search"):
        """
        Initialize TokenSearchAPI.

        Args:
            base_url: DexScreener API base URL.

        """
        self.base_url = base_url

    async def search_token(
        self, query: str, chain_id: str | None = None
    ) -> dict[str, Any] | None:
        """
        Search for a token by name or symbol and return the first matching address.

        Args:
            query: The token name or symbol (e.g., "PEPE", "WETH").
            chain_id: Optional chain filter (e.g., "ethereum", "solana", "bsc").

        Returns:
            A dictionary with 'address' and 'chain_id' if found, else None.

        """
        # Known major token addresses as fallback
        known_tokens = {
            ("WETH", "ethereum"): "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            ("WETH", "eth"): "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            ("USDC", "ethereum"): "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
            ("USDT", "ethereum"): "0xdAC17F958D2ee523a2206206994597C13D831ec7",
            ("DAI", "ethereum"): "0x6B175474E89094C44Da98b954EedeAC495271d0F",
        }

        # Check known tokens first (for major tokens like WETH)
        query_upper = query.upper()
        if chain_id:
            chain_lower = chain_id.lower()
            # Check both with and without "ethereum" alias
            keys_to_check = [
                (query_upper, chain_lower),
                (query_upper, "ethereum" if chain_lower == "eth" else chain_lower),
            ]

            for key in keys_to_check:
                if key in known_tokens:
                    known_addr = known_tokens[key]
                    # Try to get full info from DexScreener by searching the address
                    try:
                        url = f"{self.base_url}"
                        params = {"q": known_addr}
                        async with httpx.AsyncClient(timeout=10.0) as client:
                            response = await client.get(url, params=params)
                            response.raise_for_status()
                            data = response.json()
                            pairs = data.get("pairs", [])
                            if pairs:
                                pair = pairs[0]
                                token_info = pair.get("baseToken", {})
                                # Verify it's the right token
                                if token_info.get("symbol", "").upper() == query_upper:
                                    logger.info(
                                        f"Using known token address for {query_upper}"
                                    )
                                    return {
                                        "address": known_addr,
                                        "name": token_info.get("name", query),
                                        "symbol": token_info.get("symbol", query_upper),
                                        "chainId": chain_lower,
                                    }
                    except Exception as e:
                        logger.debug(
                            f"Could not fetch info for known address {known_addr}: {e}"
                        )
                        # Fall through to regular search

        # Try multiple search strategies
        queries_to_try = []

        # Strategy 1: Try trading pair format (most reliable for major tokens)
        if chain_id and chain_id.lower() in ["ethereum", "eth"]:
            queries_to_try.append(f"{query}/USDC")
            queries_to_try.append(f"{query}/USDT")

        # Strategy 2: Symbol alone (better for exact matches)
        queries_to_try.append(query)

        # Strategy 3: Symbol with chain (but avoid this for common names)
        if chain_id and query_upper not in ["WETH", "ETH", "USDC", "USDT"]:
            queries_to_try.append(f"{query} {chain_id}")

        for q in queries_to_try:
            url = f"{self.base_url}"
            params = {"q": q}

            async with httpx.AsyncClient(timeout=10.0) as client:
                try:
                    response = await client.get(url, params=params)
                    response.raise_for_status()
                    data = response.json()

                    pairs = data.get("pairs", [])
                    if not pairs:
                        continue

                    # Filter for the best match
                    if chain_id:
                        target_chain = chain_id.lower()
                        # Map common aliases
                        aliases = {
                            "ethereum": "ethereum",
                            "eth": "ethereum",
                            "bsc": "bsc",
                            "solana": "solana",
                            "sol": "solana",
                        }

                        target_canonical = aliases.get(target_chain, target_chain)

                        filtered_pairs = [
                            p
                            for p in pairs
                            if aliases.get(
                                p.get("chainId", "").lower(),
                                p.get("chainId", "").lower(),
                            )
                            == target_canonical
                        ]

                        if not filtered_pairs:
                            continue

                        # CRITICAL: Prioritize exact symbol match, then by liquidity
                        query_upper = query.upper()
                        exact_matches = [
                            p
                            for p in filtered_pairs
                            if p.get("baseToken", {}).get("symbol", "").upper()
                            == query_upper
                        ]

                        if exact_matches:
                            # Sort by liquidity (volume24h) descending
                            exact_matches.sort(
                                key=lambda x: float(
                                    x.get("volume", {}).get("h24", 0) or 0
                                ),
                                reverse=True,
                            )
                            pair = exact_matches[0]
                            # Verify the symbol matches
                            if (
                                pair.get("baseToken", {}).get("symbol", "").upper()
                                != query_upper
                            ):
                                logger.warning(
                                    f"Symbol mismatch: expected {query_upper}, got {pair.get('baseToken', {}).get('symbol')}"
                                )
                                continue  # Try next query variation
                        else:
                            # No exact match - reject if we're looking for a specific symbol
                            logger.warning(
                                f"No exact symbol match for {query_upper} on {target_canonical}"
                            )
                            continue  # Try next query variation
                    else:
                        # No chain filter - prioritize exact symbol match
                        query_upper = query.upper()
                        exact_matches = [
                            p
                            for p in pairs
                            if p.get("baseToken", {}).get("symbol", "").upper()
                            == query_upper
                        ]

                        if exact_matches:
                            exact_matches.sort(
                                key=lambda x: float(
                                    x.get("volume", {}).get("h24", 0) or 0
                                ),
                                reverse=True,
                            )
                            pair = exact_matches[0]
                        else:
                            # No exact match without chain filter - continue to next query
                            logger.debug(
                                f"No exact symbol match for {query_upper} without chain filter"
                            )
                            continue

                    result_symbol = pair.get("baseToken", {}).get("symbol", "").upper()

                    # Final validation: if we have a chain filter, ensure symbol matches
                    if chain_id and result_symbol != query_upper:
                        logger.warning(
                            f"Rejecting result: symbol {result_symbol} doesn't match query {query_upper}"
                        )
                        continue  # Try next query variation

                    result = {
                        "address": pair.get("baseToken", {}).get("address"),
                        "name": pair.get("baseToken", {}).get("name"),
                        "symbol": pair.get("baseToken", {}).get("symbol"),
                        "chainId": pair.get("chainId"),
                    }

                    logger.info(
                        f"Found token: {result['name']} ({result['symbol']}) at {result['address']} on {result['chainId']} using query '{q}'"
                    )
                    return result

                except Exception as e:
                    logger.error(f"Error searching for token {q}: {e}")
                    continue

        logger.warning(
            f"No tokens found for {query} on chain {chain_id} after trying all variations."
        )
        return None

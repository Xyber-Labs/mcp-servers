"""
This module should be changed by developers to configure blockchain networks
and payment assets for their MCP server deployment.

This is the single source of truth for all network and asset configuration.
When you clone this template and want to customize which blockchains and tokens
your service accepts for payment, edit the CUSTOM_NETWORKS dictionary below.

Main responsibilities:
- Define all supported blockchain networks and their payment assets
- Register networks with x402 payment library
- Provide derived constants for validation and block explorer links

IMPORTANT: Modify this file when you need to:
- Add support for new blockchain networks
- Configure custom token addresses for payments
- Override default network configurations from x402 library
- Change block explorer URLs
"""

import logging

from x402.mechanisms.evm.utils import NETWORK_CONFIGS

logger = logging.getLogger(__name__)


# =============================================================================
# CUSTOM NETWORK CONFIGURATIONS - MODIFY THIS SECTION
# =============================================================================

CUSTOM_NETWORKS = {
    # Base Mainnet (EVM) - Supported by x402 library by default
    "eip155:8453": {
        "chain_id": 8453,
        "explorer_url": "https://basescan.org/tx/",
        # x402 library already has Base configured, so we only need explorer URL
    },
    # Base Sepolia Testnet (EVM) - Testnet for development/testing
    "eip155:84532": {
        "chain_id": 84532,
        "explorer_url": "https://sepolia.basescan.org/tx/",
    },
    # Polygon Mainnet (EVM) - Supported by x402 library by default
    "eip155:137": {
        "chain_id": 137,
        "explorer_url": "https://polygonscan.com/tx/",
    },
    # Avalanche C-Chain (EVM) - Supported by x402 library by default
    "eip155:43114": {
        "chain_id": 43114,
        "explorer_url": "https://snowtrace.io/tx/",
    },
    # SKALE Base (L3 on Base) - Custom network, not in x402 library by default
    # Launched Jan 2026. Docs: https://docs.skale.space/welcome/skale-on-base
    "eip155:1187947933": {
        "chain_id": 1187947933,
        "explorer_url": "https://skale-base-explorer.skalenodes.com/tx/",
        "default_asset": {
            "address": "0x85889c8c714505E0c94b30fcfcF64fE3Ac8FCb20",
            "name": "Bridged USDC (SKALE Bridge)",
            "version": "2",
            "decimals": 6,
        },
        "supported_assets": {
            "USDC": {
                "address": "0x85889c8c714505E0c94b30fcfcF64fE3Ac8FCb20",
                "name": "Bridged USDC (SKALE Bridge)",
                "version": "2",
                "decimals": 6,
            },
            "USDT": {
                "address": "0x2bF5bF154b515EaA82C31a65ec11554fF5aF7fCA",
                "name": "Tether USD",
                "version": "1",
                "decimals": 6,
            },
        },
    },
    # BNB Chain (BSC) Mainnet - Custom network with XUSD
    # Using XUSD (Unibase x402 wrapped stablecoin) because it supports EIP-3009
    # for gasless payments, unlike Binance-Peg USDC
    "eip155:56": {
        "chain_id": 56,
        "explorer_url": "https://bscscan.com/tx/",
        "default_asset": {
            "address": "0xf3A3E4D9c163251124229Da6DC9C98D889647804",
            "name": "Wrapped USDC",
            "version": "2",
            "decimals": 6,
        },
        "supported_assets": {
            "XUSD": {
                "address": "0xf3A3E4D9c163251124229Da6DC9C98D889647804",
                "name": "Wrapped USDC",
                "version": "2",
                "decimals": 6,
            },
        },
    },
    # Sei Network Mainnet - Custom network
    "eip155:1329": {
        "chain_id": 1329,
        "explorer_url": "https://seitrace.com/tx/",
        "default_asset": {
            "address": "0xe15fC38F6D8c56aF07bbCBe3BAf5708A2Bf42392",
            "name": "USDC",
            "version": "2",
            "decimals": 6,
        },
        "supported_assets": {
            "USDC": {
                "address": "0xe15fC38F6D8c56aF07bbCBe3BAf5708A2Bf42392",
                "name": "USDC",
                "version": "2",
                "decimals": 6,
            },
        },
    },
    # Solana Mainnet - Supported by x402 library by default
    "solana:5eykt4UsFv8P8NJdTREpY1vzqKqZKvdp": {
        "chain_id": "solana",  # String identifier for Solana
        "explorer_url": "https://solscan.io/tx/",
    },
}

# =============================================================================
# DERIVED CONSTANTS - AUTO-GENERATED FROM CUSTOM_NETWORKS
# =============================================================================

# Mapping from chain_id to CAIP-2 network identifier
# See: https://chainagnostic.org/CAIPs/caip-2
CHAIN_ID_TO_NETWORK: dict[int | str, str] = {
    config["chain_id"]: network
    for network, config in CUSTOM_NETWORKS.items()
    if "chain_id" in config
}

# Network type classification
EVM_NETWORKS = {net for net in CUSTOM_NETWORKS.keys() if net.startswith("eip155:")}
SOLANA_NETWORKS = {net for net in CUSTOM_NETWORKS.keys() if net.startswith("solana:")}

# Block explorer URLs for transaction links
BLOCK_EXPLORERS = {
    network: config["explorer_url"]
    for network, config in CUSTOM_NETWORKS.items()
    if "explorer_url" in config
}

# =============================================================================
# X402 LIBRARY REGISTRATION
# =============================================================================


def register_custom_evm_networks() -> None:
    """
    Register custom EVM networks with the x402 payment library.

    This function iterates through CUSTOM_NETWORKS and registers any network
    that has payment asset configuration (default_asset or supported_assets)
    with x402's NETWORK_CONFIGS registry.

    Networks already in x402's registry (like Base, Polygon, Avalanche) are
    skipped unless they have custom asset configuration defined here.

    This uses direct assignment to ensure our configuration always takes
    precedence over x402 library defaults, preventing unexpected behavior
    from upstream library updates.
    """
    registered = []

    for network, config in CUSTOM_NETWORKS.items():
        # Only register networks with payment asset configuration
        if "default_asset" not in config and "supported_assets" not in config:
            continue

        # Build x402 network config (only include payment-relevant fields)
        x402_config = {
            "chain_id": config["chain_id"],
        }

        if "default_asset" in config:
            x402_config["default_asset"] = config["default_asset"]

        if "supported_assets" in config:
            x402_config["supported_assets"] = config["supported_assets"]

        # Direct assignment (overrides x402 library defaults)
        NETWORK_CONFIGS[network] = x402_config
        registered.append(network)

    if registered:
        logger.info(
            f"Registered {len(registered)} custom network(s) with x402: {', '.join(registered)}"
        )


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================


def usd_to_token_amount(usd_price: float, decimals: int) -> int:
    """
    Convert USD price to token amount based on decimals.

    Args:
        usd_price: Price in USD (e.g., 0.0001 for $0.0001)
        decimals: Token decimals (e.g., 6 for USDC, 18 for ETH)

    Returns:
        Token amount in smallest unit

    Examples:
        >>> usd_to_token_amount(0.0001, 6)  # 0.0001 USD with 6 decimals
        100
        >>> usd_to_token_amount(1.0, 6)  # 1 USD with 6 decimals
        1000000

    """
    # Assuming 1:1 USD stablecoin peg
    return int(usd_price * (10**decimals))

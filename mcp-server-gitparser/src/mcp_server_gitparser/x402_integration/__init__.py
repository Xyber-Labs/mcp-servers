"""
x402 payment integration for MCP servers.

This package encapsulates all x402 payment protocol functionality including:
- Blockchain network configuration and constants
- Payment configuration loading and validation
- USD to token amount conversion
- Block explorer URL generation

Public API:
    X402Config: Main configuration class for x402 payments
    get_x402_settings: Cached function to get X402Config instance

    # Blockchain utilities
    usd_to_token_amount: Convert USD price to token amount
    register_custom_evm_networks: Register custom EVM networks in x402 library

    # Network constants
    BLOCK_EXPLORERS: Block explorer URLs for supported networks
    CHAIN_ID_TO_NETWORK: Mapping from chain_id to CAIP-2 network identifier
    EVM_NETWORKS: Set of supported EVM network identifiers
    SOLANA_NETWORKS: Set of supported Solana network identifiers
"""

from mcp_server_gitparser.x402_integration.accepted_assets import (
    BLOCK_EXPLORERS,
    CHAIN_ID_TO_NETWORK,
    EVM_NETWORKS,
    SOLANA_NETWORKS,
    register_custom_evm_networks,
    usd_to_token_amount,
)
from mcp_server_gitparser.x402_integration.config import X402Config, get_x402_settings

__all__ = [
    # Configuration
    "X402Config",
    "get_x402_settings",
    # Blockchain utilities
    "usd_to_token_amount",
    "register_custom_evm_networks",
    # Network constants
    "BLOCK_EXPLORERS",
    "CHAIN_ID_TO_NETWORK",
    "EVM_NETWORKS",
    "SOLANA_NETWORKS",
]

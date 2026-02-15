"""Tests for accepted assets configuration and blockchain utilities."""

from mcp_server_weather.x402_integration.accepted_assets import (
    BLOCK_EXPLORERS,
    usd_to_token_amount,
)


class TestBlockExplorers:
    """Tests for block explorer configuration."""

    def test_block_explorers_configured_for_all_networks(self):
        """Test that block explorers are configured for all supported networks."""
        expected_networks = {
            "eip155:8453",  # Base
            "eip155:84532",  # Base Sepolia (testnet)
            "eip155:137",  # Polygon
            "eip155:43114",  # Avalanche
            "eip155:1187947933",  # SKALE Base
            "eip155:56",  # BNB Chain
            "eip155:1329",  # Sei Network
            "solana:5eykt4UsFv8P8NJdTREpY1vzqKqZKvdp",  # Solana
        }
        assert set(BLOCK_EXPLORERS.keys()) == expected_networks

    def test_all_explorer_urls_are_valid(self):
        """Test that all explorer URLs are properly formatted."""
        for network, url in BLOCK_EXPLORERS.items():
            assert url.startswith("https://"), f"Explorer URL for {network} should use HTTPS"
            assert url.endswith("/tx/"), f"Explorer URL for {network} should end with /tx/"

class TestUsdToTokenAmount:
    """Tests for usd_to_token_amount conversion function."""

    def test_usd_to_token_amount_6_decimals(self):
        """Test conversion with 6 decimals (typical for USDC)."""
        # $0.0001 with 6 decimals = 100 token units
        assert usd_to_token_amount(0.0001, 6) == 100

        # $1.00 with 6 decimals = 1,000,000 token units
        assert usd_to_token_amount(1.0, 6) == 1_000_000

        # $0.01 with 6 decimals = 10,000 token units
        assert usd_to_token_amount(0.01, 6) == 10_000

    def test_usd_to_token_amount_18_decimals(self):
        """Test conversion with 18 decimals (typical for ETH)."""
        # $1.00 with 18 decimals = 10^18 token units
        assert usd_to_token_amount(1.0, 18) == 10**18

        # $0.0001 with 18 decimals = 10^14 token units
        assert usd_to_token_amount(0.0001, 18) == 10**14

    def test_usd_to_token_amount_zero(self):
        """Test conversion with zero USD."""
        assert usd_to_token_amount(0.0, 6) == 0

    def test_usd_to_token_amount_fractional_result_truncated(self):
        """Test that fractional token amounts are truncated (not rounded)."""
        # 0.0000001 USD with 6 decimals = 0.1 token units -> truncated to 0
        result = usd_to_token_amount(0.0000001, 6)
        assert result == 0

        # 0.0000015 USD with 6 decimals = 1.5 token units -> truncated to 1
        result = usd_to_token_amount(0.0000015, 6)
        assert result == 1

    def test_usd_to_token_amount_large_values(self):
        """Test conversion with large USD values."""
        # $1,000,000 with 6 decimals = 1 trillion token units
        assert usd_to_token_amount(1_000_000.0, 6) == 1_000_000_000_000

    def test_usd_to_token_amount_examples_from_docstring(self):
        """Test examples from the function docstring."""
        # Example 1: $0.0001 with 6 decimals
        assert usd_to_token_amount(0.0001, 6) == 100

        # Example 2: $1.0 with 6 decimals
        assert usd_to_token_amount(1.0, 6) == 1_000_000

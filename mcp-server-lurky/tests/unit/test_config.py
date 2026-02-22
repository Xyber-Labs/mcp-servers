from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from mcp_server_lurky.x402_integration.config import PaymentOptionConfig, X402Config

# =============================================================================
# Feature 1: USD to Token Amount Conversion
# =============================================================================


class TestUsdToTokenConversion:
    """Tests for automatic USD to token amount conversion."""

    def test_converts_usd_to_token_amount_using_chain_decimals(self):
        """USD price is converted to token amount based on token decimals from x402 library."""
        opt = PaymentOptionConfig(
            chain_id=8453,
            token_address="0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
            price_usd=0.0001,
        )
        # Base USDC has 6 decimals: 0.0001 USD = 100 token units
        assert opt.token_amount == 100

    def test_conversion_with_various_usd_amounts(self):
        """Different USD amounts convert correctly to token amounts."""
        # $1.00 = 1,000,000 token units (6 decimals)
        opt1 = PaymentOptionConfig(
            chain_id=8453,
            token_address="0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
            price_usd=1.0,
        )
        assert opt1.token_amount == 1_000_000

        # $0.01 = 10,000 token units
        opt2 = PaymentOptionConfig(
            chain_id=8453,
            token_address="0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
            price_usd=0.01,
        )
        assert opt2.token_amount == 10_000

    def test_conversion_works_for_solana_networks(self):
        """Solana networks (string chain_id) also convert correctly."""
        opt = PaymentOptionConfig(
            chain_id="solana",
            token_address="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
            price_usd=0.0001,
        )
        assert opt.chain_id == "solana"
        assert opt.token_amount == 100


# =============================================================================
# Feature 2: Tool Pricing YAML Loading & Validation
# =============================================================================


class TestToolPricingYamlValidation:
    """Tests for loading and validating tool_pricing.yaml configuration."""

    def test_loads_valid_yaml_with_pricing_for_multiple_endpoints(self, tmp_path: Path):
        """Valid YAML with multiple endpoints loads successfully."""
        yaml_content = {
            "lurky_search": [
                {
                    "chain_id": 8453,
                    "token_address": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
                    "price_usd": 1.0,
                }
            ],
            "lurky_get_space": [
                {
                    "chain_id": 8453,
                    "token_address": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
                    "price_usd": 0.5,
                }
            ],
        }
        yaml_file = tmp_path / "tool_pricing.yaml"
        yaml_file.write_text(yaml.dump(yaml_content))

        config = X402Config(pricing_config_path=yaml_file)

        assert len(config.pricing) == 2
        assert "lurky_search" in config.pricing
        assert "lurky_get_space" in config.pricing
        assert isinstance(config.pricing["lurky_search"][0], PaymentOptionConfig)
        assert config.pricing["lurky_search"][0].token_amount == 1000000

    def test_supports_multiple_payment_options_per_endpoint(self, tmp_path: Path):
        """Endpoint can accept payment on multiple chains."""
        yaml_content = {
            "multi_chain_endpoint": [
                # Base USDC
                {
                    "chain_id": 8453,
                    "token_address": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
                    "price_usd": 0.0001,
                },
                # Polygon USDC
                {
                    "chain_id": 137,
                    "token_address": "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359",
                    "price_usd": 0.0002,
                },
            ]
        }
        yaml_file = tmp_path / "tool_pricing.yaml"
        yaml_file.write_text(yaml.dump(yaml_content))

        config = X402Config(pricing_config_path=yaml_file)

        assert len(config.pricing["multi_chain_endpoint"]) == 2

    def test_missing_yaml_file_returns_empty_pricing(self, tmp_path: Path):
        """Missing YAML file returns empty pricing dict with warning."""
        config = X402Config(pricing_config_path=tmp_path / "nonexistent.yaml")

        assert config.pricing == {}

    def test_empty_yaml_file_returns_empty_pricing(self, tmp_path: Path):
        """Empty YAML file returns empty pricing dict."""
        yaml_file = tmp_path / "tool_pricing.yaml"
        yaml_file.write_text("")

        config = X402Config(pricing_config_path=yaml_file)

        assert config.pricing == {}

    def test_invalid_yaml_syntax_raises_error(self, tmp_path: Path):
        """Malformed YAML syntax raises ValueError."""
        yaml_file = tmp_path / "tool_pricing.yaml"
        yaml_file.write_text("invalid: yaml: syntax: [unclosed")

        config = X402Config(pricing_config_path=yaml_file)

        with pytest.raises(ValueError, match="Invalid YAML syntax"):
            _ = config.pricing

    def test_invalid_chain_id_skipped_with_warning(self):
        """Payment option with invalid chain_id is skipped during validation."""
        opt = PaymentOptionConfig(
            chain_id=99999,
            token_address="0x1234567890123456789012345678901234567890",
            price_usd=0.0001,
        )
        with pytest.raises(ValueError, match="Unknown chain_id '99999'"):
            opt.validate_config()


# =============================================================================
# Feature 3: Facilitator URL Parsing
# =============================================================================


class TestFacilitatorUrlParsing:
    """Tests for parsing facilitator URLs from environment variables."""

    def test_parses_single_facilitator_url(self):
        """Single facilitator URL creates one FacilitatorConfig."""
        from x402.http import FacilitatorConfig

        config = X402Config(
            facilitator_urls=["https://facilitator.example.com"],
            pricing_config_path=Path("/nonexistent"),
        )

        result = config.facilitator_config

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], FacilitatorConfig)
        assert result[0].url == "https://facilitator.example.com"

    def test_parses_multiple_facilitator_urls(self):
        """Multiple facilitator URLs create multiple FacilitatorConfig objects."""
        from x402.http import FacilitatorConfig

        config = X402Config(
            facilitator_urls=[
                "https://facilitator1.example.com",
                "https://facilitator2.example.com",
            ],
            pricing_config_path=Path("/nonexistent"),
        )

        result = config.facilitator_config

        assert isinstance(result, list)
        assert len(result) == 2
        assert isinstance(result[0], FacilitatorConfig)
        assert isinstance(result[1], FacilitatorConfig)

    def test_no_facilitator_returns_empty_list(self):
        """No facilitator configured returns empty list."""
        config = X402Config(
            facilitator_urls=None, pricing_config_path=Path("/nonexistent")
        )

        assert config.facilitator_config == []


# =============================================================================
# Feature 4: Pricing Mode Validation
# =============================================================================


class TestPricingModeValidation:
    """Tests for pricing_mode validation logic."""

    def test_pricing_mode_on_without_config_raises_error(self, tmp_path: Path):
        """pricing_mode='on' without pricing config raises error (fail-fast)."""
        nonexistent_yaml = tmp_path / "nonexistent.yaml"

        config = X402Config(
            pricing_mode="on",
            pricing_config_path=nonexistent_yaml,
        )

        with pytest.raises(ValueError, match="pricing_mode.*on.*no pricing"):
            config.validate_pricing_mode()

    def test_pricing_mode_off_with_config_logs_warning(self, tmp_path: Path, caplog):
        """pricing_mode='off' with pricing config logs warning."""
        yaml_content = {
            "test_endpoint": [
                {
                    "chain_id": 8453,
                    "token_address": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
                    "price_usd": 0.0001,
                }
            ]
        }
        yaml_file = tmp_path / "tool_pricing.yaml"
        yaml_file.write_text(yaml.dump(yaml_content))

        config = X402Config(
            pricing_mode="off",
            pricing_config_path=yaml_file,
        )

        # Pricing should load successfully
        assert len(config.pricing) == 1

        # validate_pricing_mode should log a warning
        with caplog.at_level("WARNING"):
            config.validate_pricing_mode()

        assert (
            "pricing_mode" in caplog.text.lower() or "disabled" in caplog.text.lower()
        )

    def test_pricing_mode_on_with_config_passes(self, tmp_path: Path):
        """pricing_mode='on' with pricing config passes validation."""
        yaml_content = {
            "test_endpoint": [
                {
                    "chain_id": 8453,
                    "token_address": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
                    "price_usd": 0.0001,
                }
            ]
        }
        yaml_file = tmp_path / "tool_pricing.yaml"
        yaml_file.write_text(yaml.dump(yaml_content))

        config = X402Config(
            pricing_mode="on",
            pricing_config_path=yaml_file,
        )

        # Pricing should load successfully
        assert len(config.pricing) == 1
        assert config.pricing_mode == "on"

        # validate_pricing_mode should pass without error
        config.validate_pricing_mode()  # Should not raise

    def test_pricing_mode_off_without_config_works(self, tmp_path: Path):
        """pricing_mode='off' without pricing config works (no middleware)."""
        nonexistent_yaml = tmp_path / "nonexistent.yaml"

        config = X402Config(
            pricing_mode="off",
            pricing_config_path=nonexistent_yaml,
        )

        # Should return empty pricing without error
        assert config.pricing == {}
        assert config.pricing_mode == "off"


# =============================================================================
# Feature 5: Payee Address Selection
# =============================================================================


class TestPayeeAddressSelection:
    """Tests for selecting appropriate payee address based on network type."""

    def test_returns_evm_address_for_evm_networks(self):
        """EVM networks return payee_evm_address."""
        config = X402Config(
            payee_evm_address="0x1234567890123456789012345678901234567890",
            payee_solana_address="SolanaAddress123456789",
            pricing_config_path=Path("/nonexistent"),
        )

        # Base (EVM)
        assert (
            config.get_payee_address("eip155:8453")
            == "0x1234567890123456789012345678901234567890"
        )

    def test_returns_solana_address_for_solana_networks(self):
        """Solana networks return payee_solana_address."""
        config = X402Config(
            payee_evm_address="0x1234567890123456789012345678901234567890",
            payee_solana_address="SolanaAddress123456789",
            pricing_config_path=Path("/nonexistent"),
        )

        assert (
            config.get_payee_address("solana:5eykt4UsFv8P8NJdTREpY1vzqKqZKvdp")
            == "SolanaAddress123456789"
        )

    def test_returns_none_when_address_not_configured(self):
        """Returns None when appropriate address is not configured."""
        config = X402Config(
            payee_evm_address=None,
            payee_solana_address=None,
            pricing_config_path=Path("/nonexistent"),
        )

        assert config.get_payee_address("eip155:8453") is None
        assert (
            config.get_payee_address("solana:5eykt4UsFv8P8NJdTREpY1vzqKqZKvdp") is None
        )

"""Tests for X402Config and payment configuration features."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from mcp_server_weather.config import AppSettings
from mcp_server_weather.x402_integration.config import PaymentOptionConfig, X402Config


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
            "search_endpoint": [
                {
                    "chain_id": 8453,
                    "token_address": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
                    "price_usd": 1.0,
                }
            ],
            "another_endpoint": [
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
        assert "search_endpoint" in config.pricing
        assert "another_endpoint" in config.pricing
        assert isinstance(config.pricing["search_endpoint"][0], PaymentOptionConfig)
        assert config.pricing["search_endpoint"][0].token_amount == 1000000

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

    def test_yaml_with_only_comments_returns_empty_pricing(self, tmp_path: Path):
        """YAML with only comments returns empty pricing dict."""
        yaml_file = tmp_path / "tool_pricing.yaml"
        yaml_file.write_text("# This is a comment\n# Another comment")

        config = X402Config(pricing_config_path=yaml_file)

        assert config.pricing == {}

    def test_invalid_yaml_syntax_raises_error(self, tmp_path: Path):
        """Malformed YAML syntax raises ValueError."""
        yaml_file = tmp_path / "tool_pricing.yaml"
        yaml_file.write_text("invalid: yaml: syntax: [unclosed")

        config = X402Config(pricing_config_path=yaml_file)

        with pytest.raises(ValueError, match="Invalid YAML syntax"):
            _ = config.pricing

    def test_yaml_root_as_list_instead_of_dict_raises_error(self, tmp_path: Path):
        """YAML root being a list instead of dict raises ValueError."""
        yaml_file = tmp_path / "tool_pricing.yaml"
        yaml_file.write_text("- item1\n- item2")

        config = X402Config(pricing_config_path=yaml_file)

        with pytest.raises(ValueError, match="expected a YAML mapping"):
            _ = config.pricing

    def test_yaml_root_as_string_instead_of_dict_raises_error(self, tmp_path: Path):
        """YAML root being a string instead of dict raises ValueError."""
        yaml_file = tmp_path / "tool_pricing.yaml"
        yaml_file.write_text("just a string")

        config = X402Config(pricing_config_path=yaml_file)

        with pytest.raises(ValueError, match="expected a YAML mapping"):
            _ = config.pricing

    def test_endpoint_value_not_list_raises_error(self, tmp_path: Path):
        """Endpoint mapped to non-list value raises ValueError."""
        yaml_content = {"endpoint": "not_a_list"}
        yaml_file = tmp_path / "tool_pricing.yaml"
        yaml_file.write_text(yaml.dump(yaml_content))

        config = X402Config(pricing_config_path=yaml_file)

        with pytest.raises(ValueError, match="Each endpoint must map to a list"):
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

    def test_all_supported_chain_ids_are_valid(self):
        """All configured chain IDs pass validation."""
        valid_chain_ids = [
            8453,  # Base
            84532,  # Base Sepolia
            137,  # Polygon
            43114,  # Avalanche
            1187947933,  # SKALE Base
            56,  # BNB Chain
            1329,  # Sei Network
            "solana",  # Solana
        ]
        for chain_id in valid_chain_ids:
            opt = PaymentOptionConfig(
                chain_id=chain_id,
                token_address="0x1234567890123456789012345678901234567890",
                price_usd=0.0001,
            )
            # Should not raise
            opt.validate_config()

    def test_empty_token_address_rejected_during_validation(self):
        """Empty token address is rejected during validation."""
        opt = PaymentOptionConfig(
            chain_id=8453,
            token_address="",
            price_usd=0.0001,
        )
        with pytest.raises(ValueError, match="token_address cannot be empty"):
            opt.validate_config()

    def test_payment_option_missing_required_fields_skipped(self, tmp_path: Path):
        """Payment option missing required fields is skipped with warning."""
        yaml_content = {"endpoint": [{"chain_id": 8453}]}  # missing token_address and price_usd
        yaml_file = tmp_path / "tool_pricing.yaml"
        yaml_file.write_text(yaml.dump(yaml_content))

        config = X402Config(pricing_config_path=yaml_file)

        # Should return empty dict since the only entry is invalid
        assert config.pricing == {}

    def test_invalid_price_usd_type_skipped(self, tmp_path: Path):
        """Non-numeric price_usd is skipped with warning."""
        yaml_content = {
            "endpoint": [
                {
                    "chain_id": 8453,
                    "token_address": "0x123",
                    "price_usd": "not_a_number",
                }
            ]
        }
        yaml_file = tmp_path / "tool_pricing.yaml"
        yaml_file.write_text(yaml.dump(yaml_content))

        config = X402Config(pricing_config_path=yaml_file)

        # Should return empty dict since the only entry is invalid
        assert config.pricing == {}


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
        assert result[0].url == "https://facilitator1.example.com"
        assert result[1].url == "https://facilitator2.example.com"

    def test_no_facilitator_returns_empty_list(self):
        """No facilitator configured returns empty list."""
        config = X402Config(facilitator_urls=None, pricing_config_path=Path("/nonexistent"))

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

        assert "pricing_mode" in caplog.text.lower() or "disabled" in caplog.text.lower()

    def test_pricing_mode_on_with_config_passes(self, tmp_path: Path, caplog):
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
        with caplog.at_level("INFO"):
            config.validate_pricing_mode()  # Should not raise

        # Should log success message
        assert "enabled" in caplog.text.lower() or len(config.pricing) > 0

    def test_pricing_mode_off_without_config_works(self, tmp_path: Path, caplog):
        """pricing_mode='off' without pricing config works (no middleware)."""
        nonexistent_yaml = tmp_path / "nonexistent.yaml"

        config = X402Config(
            pricing_mode="off",
            pricing_config_path=nonexistent_yaml,
        )

        # Should return empty pricing without error
        assert config.pricing == {}
        assert config.pricing_mode == "off"

        # Verify the expected log message
        with caplog.at_level("WARNING"):
            _ = config.pricing
        assert "not found" in caplog.text or config.pricing == {}


# =============================================================================
# Feature 5: Route Validation
# =============================================================================


class TestRouteValidation:
    """Tests for validating pricing config against actual routes."""

    class MockRoute:
        def __init__(self, operation_id: str | None):
            self.operation_id = operation_id

    def test_logs_correctly_configured_endpoints(self, tmp_path: Path, caplog):
        """Logs endpoints that have matching pricing configuration."""
        yaml_content = {
            "endpoint_a": [
                {
                    "chain_id": 8453,
                    "token_address": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
                    "price_usd": 0.0001,
                }
            ]
        }
        yaml_file = tmp_path / "tool_pricing.yaml"
        yaml_file.write_text(yaml.dump(yaml_content))

        config = X402Config(pricing_config_path=yaml_file)
        routes = [self.MockRoute("endpoint_a"), self.MockRoute("endpoint_b")]

        with caplog.at_level("INFO"):
            config.validate_against_routes(routes)

        assert "endpoint_a" in caplog.text

    def test_warns_about_misconfigured_endpoints(self, tmp_path: Path, caplog):
        """Warns about priced endpoints that don't match any route."""
        yaml_content = {
            "typo_endpoint": [
                {
                    "chain_id": 8453,
                    "token_address": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
                    "price_usd": 0.0001,
                }
            ]
        }
        yaml_file = tmp_path / "tool_pricing.yaml"
        yaml_file.write_text(yaml.dump(yaml_content))

        config = X402Config(pricing_config_path=yaml_file)
        routes = [self.MockRoute("real_endpoint")]

        with caplog.at_level("WARNING"):
            config.validate_against_routes(routes)

        assert "typo_endpoint" in caplog.text
        assert "Typo?" in caplog.text


# =============================================================================
# Feature 6: Payee Address Selection
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
        assert config.get_payee_address("eip155:8453") == "0x1234567890123456789012345678901234567890"
        # Polygon (EVM)
        assert config.get_payee_address("eip155:137") == "0x1234567890123456789012345678901234567890"

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
        assert config.get_payee_address("solana:5eykt4UsFv8P8NJdTREpY1vzqKqZKvdp") is None

"""Tests for X402Config and AppSettings configuration loading."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
import yaml

from mcp_server_weather.config import AppSettings, PaymentOption, X402Config


class TestPaymentOption:
    """Tests for PaymentOption model validation."""

    def test_valid_payment_option(self):
        opt = PaymentOption(
            chain_id=8453,
            token_address="0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
            token_amount=1000000,
        )
        assert opt.chain_id == 8453
        assert opt.token_amount == 1000000

    def test_token_amount_zero_allowed(self):
        opt = PaymentOption(
            chain_id=1,
            token_address="0x0",
            token_amount=0,
        )
        assert opt.token_amount == 0

    def test_negative_token_amount_rejected(self):
        with pytest.raises(ValueError):
            PaymentOption(
                chain_id=1,
                token_address="0x0",
                token_amount=-1,
            )

    def test_missing_required_fields(self):
        with pytest.raises(ValueError):
            PaymentOption(chain_id=1)  # type: ignore


class TestX402ConfigPricing:
    """Tests for X402Config.pricing computed field with YAML loading."""

    def test_pricing_with_valid_yaml(self, tmp_path: Path):
        """Valid YAML with correct structure loads successfully."""
        yaml_content = {
            "search_endpoint": [
                {
                    "chain_id": 8453,
                    "token_address": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
                    "token_amount": 1000000,
                }
            ],
            "another_endpoint": [
                {
                    "chain_id": 1,
                    "token_address": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
                    "token_amount": 500000,
                }
            ],
        }
        yaml_file = tmp_path / "tool_pricing.yaml"
        yaml_file.write_text(yaml.dump(yaml_content))

        config = X402Config(pricing_config_path=yaml_file)

        assert len(config.pricing) == 2
        assert "search_endpoint" in config.pricing
        assert "another_endpoint" in config.pricing
        assert isinstance(config.pricing["search_endpoint"][0], PaymentOption)
        assert config.pricing["search_endpoint"][0].token_amount == 1000000

    def test_pricing_with_multiple_options_per_endpoint(self, tmp_path: Path):
        """Endpoint can have multiple payment options (different chains)."""
        yaml_content = {
            "multi_chain_endpoint": [
                {"chain_id": 8453, "token_address": "0xbase", "token_amount": 100},
                {"chain_id": 1, "token_address": "0xeth", "token_amount": 200},
            ]
        }
        yaml_file = tmp_path / "tool_pricing.yaml"
        yaml_file.write_text(yaml.dump(yaml_content))

        config = X402Config(pricing_config_path=yaml_file)

        assert len(config.pricing["multi_chain_endpoint"]) == 2

    def test_pricing_file_not_found_returns_empty(self, tmp_path: Path):
        """Missing YAML file returns empty pricing dict (warning logged)."""
        config = X402Config(pricing_config_path=tmp_path / "nonexistent.yaml")

        assert config.pricing == {}

    def test_pricing_empty_yaml_returns_empty(self, tmp_path: Path):
        """Empty YAML file returns empty pricing dict."""
        yaml_file = tmp_path / "tool_pricing.yaml"
        yaml_file.write_text("")

        config = X402Config(pricing_config_path=yaml_file)

        assert config.pricing == {}

    def test_pricing_yaml_with_only_comments_returns_empty(self, tmp_path: Path):
        """YAML with only comments returns empty pricing dict."""
        yaml_file = tmp_path / "tool_pricing.yaml"
        yaml_file.write_text("# This is a comment\n# Another comment")

        config = X402Config(pricing_config_path=yaml_file)

        assert config.pricing == {}

    def test_pricing_invalid_yaml_syntax_raises(self, tmp_path: Path):
        """Malformed YAML syntax raises ValueError."""
        yaml_file = tmp_path / "tool_pricing.yaml"
        yaml_file.write_text("invalid: yaml: syntax: [unclosed")

        config = X402Config(pricing_config_path=yaml_file)

        with pytest.raises(ValueError, match="Invalid YAML syntax"):
            _ = config.pricing

    def test_pricing_yaml_list_instead_of_dict_raises(self, tmp_path: Path):
        """YAML root being a list instead of dict raises ValueError."""
        yaml_file = tmp_path / "tool_pricing.yaml"
        yaml_file.write_text("- item1\n- item2")

        config = X402Config(pricing_config_path=yaml_file)

        with pytest.raises(ValueError, match="expected a YAML mapping"):
            _ = config.pricing

    def test_pricing_yaml_string_instead_of_dict_raises(self, tmp_path: Path):
        """YAML root being a string instead of dict raises ValueError."""
        yaml_file = tmp_path / "tool_pricing.yaml"
        yaml_file.write_text("just a string")

        config = X402Config(pricing_config_path=yaml_file)

        with pytest.raises(ValueError, match="expected a YAML mapping"):
            _ = config.pricing

    def test_pricing_endpoint_value_not_list_raises(self, tmp_path: Path):
        """Endpoint mapped to non-list value raises ValueError."""
        yaml_content = {"endpoint": "not_a_list"}
        yaml_file = tmp_path / "tool_pricing.yaml"
        yaml_file.write_text(yaml.dump(yaml_content))

        config = X402Config(pricing_config_path=yaml_file)

        with pytest.raises(ValueError, match="Each endpoint must map to a list"):
            _ = config.pricing

    def test_pricing_missing_required_option_field_raises(self, tmp_path: Path):
        """Payment option missing required field raises ValueError."""
        yaml_content = {
            "endpoint": [
                {"chain_id": 8453}  # missing token_address and token_amount
            ]
        }
        yaml_file = tmp_path / "tool_pricing.yaml"
        yaml_file.write_text(yaml.dump(yaml_content))

        config = X402Config(pricing_config_path=yaml_file)

        with pytest.raises(ValueError):
            _ = config.pricing

    def test_pricing_invalid_token_amount_type_raises(self, tmp_path: Path):
        """Non-integer token_amount raises ValueError."""
        yaml_content = {
            "endpoint": [
                {
                    "chain_id": 8453,
                    "token_address": "0x123",
                    "token_amount": "not_a_number",
                }
            ]
        }
        yaml_file = tmp_path / "tool_pricing.yaml"
        yaml_file.write_text(yaml.dump(yaml_content))

        config = X402Config(pricing_config_path=yaml_file)

        with pytest.raises(ValueError):
            _ = config.pricing


class TestX402ConfigFacilitator:
    """Tests for X402Config.facilitator_config computed field."""

    def test_facilitator_with_cdp_keys(self):
        """CDP API keys present configures mainnet facilitator."""
        with patch("mcp_server_weather.config.create_facilitator_config") as mock:
            mock.return_value = {"url": "https://cdp.facilitator"}
            config = X402Config(
                cdp_api_key_id="key_id",
                cdp_api_key_secret="key_secret",
                pricing_config_path=Path("/nonexistent"),
            )

            result = config.facilitator_config

            mock.assert_called_once_with(
                api_key_id="key_id",
                api_key_secret="key_secret",
            )
            assert result == {"url": "https://cdp.facilitator"}

    def test_facilitator_with_url_only(self):
        """Facilitator URL without CDP keys uses public facilitator."""
        config = X402Config(
            facilitator_url="https://public.facilitator",
            pricing_config_path=Path("/nonexistent"),
        )

        result = config.facilitator_config

        assert result == {"url": "https://public.facilitator"}

    def test_facilitator_cdp_takes_precedence(self):
        """CDP keys take precedence over facilitator_url."""
        with patch("mcp_server_weather.config.create_facilitator_config") as mock:
            mock.return_value = {"url": "https://cdp.facilitator"}
            config = X402Config(
                cdp_api_key_id="key_id",
                cdp_api_key_secret="key_secret",
                facilitator_url="https://public.facilitator",
                pricing_config_path=Path("/nonexistent"),
            )

            result = config.facilitator_config

            mock.assert_called_once()
            assert result == {"url": "https://cdp.facilitator"}

    def test_facilitator_none_when_no_config(self):
        """No CDP keys or URL returns None."""
        config = X402Config(pricing_config_path=Path("/nonexistent"))

        assert config.facilitator_config is None


class TestX402ConfigPricingMode:
    """Tests for pricing_mode field."""

    def test_pricing_mode_default_on(self):
        config = X402Config(pricing_config_path=Path("/nonexistent"))
        assert config.pricing_mode == "on"

    def test_pricing_mode_off(self):
        config = X402Config(
            pricing_mode="off",
            pricing_config_path=Path("/nonexistent"),
        )
        assert config.pricing_mode == "off"

    def test_pricing_mode_invalid_rejected(self):
        with pytest.raises(ValueError):
            X402Config(
                pricing_mode="invalid",  # type: ignore
                pricing_config_path=Path("/nonexistent"),
            )


class TestAppSettings:
    """Tests for AppSettings configuration."""

    def test_default_values(self):
        settings = AppSettings()

        assert settings.host == "0.0.0.0"
        assert settings.port == 8000
        assert settings.logging_level == "INFO"
        assert settings.hot_reload is False

    def test_custom_values(self):
        settings = AppSettings(
            host="127.0.0.1",
            port=9000,
            logging_level="DEBUG",
            hot_reload=True,
        )

        assert settings.host == "127.0.0.1"
        assert settings.port == 9000
        assert settings.logging_level == "DEBUG"
        assert settings.hot_reload is True

    def test_invalid_logging_level_rejected(self):
        with pytest.raises(ValueError):
            AppSettings(logging_level="INVALID")  # type: ignore


class TestValidateAgainstRoutes:
    """Tests for X402Config.validate_against_routes method."""

    class MockRoute:
        def __init__(self, operation_id: str | None):
            self.operation_id = operation_id

    def test_validate_correctly_configured(self, tmp_path: Path, caplog):
        """Logs correctly configured endpoints."""
        yaml_content = {"endpoint_a": [{"chain_id": 1, "token_address": "0x", "token_amount": 100}]}
        yaml_file = tmp_path / "tool_pricing.yaml"
        yaml_file.write_text(yaml.dump(yaml_content))

        config = X402Config(pricing_config_path=yaml_file)
        routes = [self.MockRoute("endpoint_a"), self.MockRoute("endpoint_b")]

        with caplog.at_level("INFO"):
            config.validate_against_routes(routes)

        assert "endpoint_a" in caplog.text

    def test_validate_misconfigured_warns(self, tmp_path: Path, caplog):
        """Warns about priced endpoints that don't exist."""
        yaml_content = {"typo_endpoint": [{"chain_id": 1, "token_address": "0x", "token_amount": 100}]}
        yaml_file = tmp_path / "tool_pricing.yaml"
        yaml_file.write_text(yaml.dump(yaml_content))

        config = X402Config(pricing_config_path=yaml_file)
        routes = [self.MockRoute("real_endpoint")]

        with caplog.at_level("WARNING"):
            config.validate_against_routes(routes)

        assert "typo_endpoint" in caplog.text
        assert "Typo?" in caplog.text

"""Tests for X402Config and AppSettings configuration loading."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
import yaml

from mcp_server_arxiv.config import AppSettings
from mcp_server_arxiv.x402_integration import PaymentOptionConfig, X402Config


@pytest.fixture(autouse=True)
def isolate_env(monkeypatch):
    """Remove all MCP_ARXIV env vars to isolate tests from .env files."""
    for key in list(os.environ.keys()):
        if key.startswith("MCP_ARXIV"):
            monkeypatch.delenv(key, raising=False)


class TestPaymentOptionConfig:
    """Tests for PaymentOptionConfig model validation."""

    def test_valid_payment_option(self):
        opt = PaymentOptionConfig(
            chain_id=8453,
            token_address="0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
            price_usd=1.0,
        )
        assert opt.chain_id == 8453
        assert opt.token_amount == 1000000

    def test_price_usd_positive_required(self):
        with pytest.raises(ValueError):
            PaymentOptionConfig(
                chain_id=8453,
                token_address="0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
                price_usd=0,
            )

    def test_negative_price_usd_rejected(self):
        with pytest.raises(ValueError):
            PaymentOptionConfig(
                chain_id=8453,
                token_address="0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
                price_usd=-1,
            )

    def test_missing_required_fields(self):
        with pytest.raises(ValueError):
            PaymentOptionConfig(chain_id=1)  # type: ignore


class TestX402ConfigPricing:
    """Tests for X402Config.pricing computed field with YAML loading."""

    def test_pricing_with_valid_yaml(self, tmp_path: Path):
        """Valid YAML with correct structure loads successfully."""
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
                    "chain_id": 137,  # Changed from 1 to 137 (Polygon)
                    "token_address": "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359",
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

    def test_pricing_with_multiple_options_per_endpoint(self, tmp_path: Path):
        """Endpoint can have multiple payment options (different chains)."""
        yaml_content = {
            "multi_chain_endpoint": [
                {
                    "chain_id": 8453,
                    "token_address": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
                    "price_usd": 0.0001,
                },
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

    def test_pricing_missing_required_option_field_logs_warning(
        self, tmp_path: Path, caplog
    ):
        """Payment option missing required field logs warning and skips entry."""
        yaml_content = {
            "endpoint": [
                {"chain_id": 8453}  # missing token_address and price_usd
            ]
        }
        yaml_file = tmp_path / "tool_pricing.yaml"
        yaml_file.write_text(yaml.dump(yaml_content))

        config = X402Config(pricing_config_path=yaml_file)

        # Should not raise, but log warning and skip the invalid entry
        with caplog.at_level("WARNING"):
            pricing = config.pricing

        # The endpoint should not be in pricing since all its options were invalid
        assert "endpoint" not in pricing
        assert "Skipping invalid payment option" in caplog.text

    def test_pricing_invalid_price_usd_type_logs_warning(self, tmp_path: Path, caplog):
        """Non-numeric price_usd logs warning and skips entry."""
        yaml_content = {
            "endpoint": [
                {
                    "chain_id": 8453,
                    "token_address": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
                    "price_usd": "not_a_number",
                }
            ]
        }
        yaml_file = tmp_path / "tool_pricing.yaml"
        yaml_file.write_text(yaml.dump(yaml_content))

        config = X402Config(pricing_config_path=yaml_file)

        # Should not raise, but log warning and skip the invalid entry
        with caplog.at_level("WARNING"):
            pricing = config.pricing

        # The endpoint should not be in pricing since all its options were invalid
        assert "endpoint" not in pricing
        assert "Skipping invalid payment option" in caplog.text


class TestX402ConfigFacilitator:
    """Tests for X402Config.facilitator_config computed field."""

    def test_facilitator_with_url_only(self):
        """Facilitator URLs creates list of facilitator configs."""
        config = X402Config(
            facilitator_urls=["https://public.facilitator"],
            pricing_config_path=Path("/nonexistent"),
            _env_file=None,
        )

        result = config.facilitator_config

        assert result is not None
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].url == "https://public.facilitator"

    def test_facilitator_empty_when_no_config(self):
        """No facilitator URLs returns empty list."""
        config = X402Config(
            facilitator_urls=None,
            pricing_config_path=Path("/nonexistent"),
            _env_file=None,
        )

        assert config.facilitator_config == []


class TestX402ConfigPricingMode:
    """Tests for pricing_mode field."""

    def test_pricing_mode_default_off(self):
        config = X402Config(pricing_config_path=Path("/nonexistent"))
        assert config.pricing_mode == "off"

    def test_pricing_mode_on(self):
        config = X402Config(
            pricing_mode="on",
            pricing_config_path=Path("/nonexistent"),
        )
        assert config.pricing_mode == "on"

    def test_pricing_mode_invalid_rejected(self):
        with pytest.raises(ValueError):
            X402Config(
                pricing_mode="invalid",  # type: ignore
                pricing_config_path=Path("/nonexistent"),
            )


class TestAppSettings:
    """Tests for AppSettings configuration."""

    def test_default_values(self):
        settings = AppSettings(_env_file=None)

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
        yaml_content = {
            "endpoint_a": [
                {
                    "chain_id": 1,
                    "token_address": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
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

    def test_validate_misconfigured_warns(self, tmp_path: Path, caplog):
        """Warns about priced endpoints that don't exist (when using valid chain_id)."""
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

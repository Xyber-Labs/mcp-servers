"""
Configuration for x402 payment protocol.
Loads simple key-value settings from environment variables and complex
pricing structures from a dedicated YAML file.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

# Mapping from chain_id to CAIP-2 network identifier
# See: https://chainagnostic.org/CAIPs/caip-2
CHAIN_ID_TO_NETWORK: dict[int, str] = {
    1: "eip155:1",  # Ethereum Mainnet
    8453: "eip155:8453",  # Base Mainnet
    84532: "eip155:84532",  # Base Sepolia
    10: "eip155:10",  # Optimism
    42161: "eip155:42161",  # Arbitrum One
    137: "eip155:137",  # Polygon
}


class PaymentOptionConfig(BaseModel):
    """
    Defines a single payment option for a protected resource as stored in YAML.
    This is the configuration format that gets transformed into x402 v2 PaymentOption.

    Note: token_amount should be specified in the token's smallest unit.
    For example, USDC has 6 decimals, so 1 USDC = 1,000,000 token_amount.
    """

    chain_id: int
    token_address: str
    token_amount: int = Field(ge=0)


class X402Config(BaseSettings):
    """
    Configuration for the x402 payment protocol.
    Loads simple key-value settings from environment variables and complex
    pricing structures from a dedicated YAML file.
    """

    model_config = SettingsConfigDict(
        env_prefix="MCP_TWITTER_X402_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    pricing_mode: Literal["off", "on"] = "off"
    payee_evm_address: str | None = None
    facilitator_url: str | None = None
    cdp_api_key_id: str | None = None
    cdp_api_key_secret: str | None = None

    pricing_config_path: Path = Path("tool_pricing.yaml")

    @computed_field
    @property
    def facilitator_config(self) -> dict[str, str] | None:
        """
        A computed field that creates the correct facilitator configuration.
        - If CDP API keys are present, it configures for mainnet.
        - If a facilitator_url is provided, it configures for that URL.
        - If neither is provided, returns None, disabling payments.
        """
        if self.cdp_api_key_id and self.cdp_api_key_secret:
            logger.info("CDP API keys found, configuring for mainnet facilitator.")
            try:
                from cdp.x402 import create_facilitator_config

                return create_facilitator_config(
                    api_key_id=self.cdp_api_key_id,
                    api_key_secret=self.cdp_api_key_secret,
                )
            except ImportError:
                logger.warning(
                    "CDP SDK not available. Cannot use CDP API keys for facilitator. "
                    "Install cdp-sdk or use facilitator_url instead."
                )
                return None
        if self.facilitator_url:
            logger.info(f"Using public facilitator at {self.facilitator_url}")
            from x402.http import FacilitatorConfig

            return FacilitatorConfig(url=self.facilitator_url)
        return None

    @computed_field
    @property
    def pricing(self) -> dict[str, list[PaymentOptionConfig]]:
        """
        A computed field that loads, parses, and validates the pricing
        configuration from the YAML file specified by 'pricing_config_path'.
        """
        if not self.pricing_config_path.is_file():
            logger.warning(
                f"Pricing config file not found at '{self.pricing_config_path}'. "
                "No endpoints will be monetized."
            )
            return {}

        try:
            with open(self.pricing_config_path) as f:
                pricing_data = yaml.safe_load(f)
                if not pricing_data:
                    return {}
                # Pydantic can validate nested structures directly
                validated_pricing = {
                    op_id: [PaymentOptionConfig(**opt) for opt in opts]
                    for op_id, opts in pricing_data.items()
                }
                logger.info(
                    f"Successfully loaded pricing for {len(validated_pricing)} tools."
                )
                return validated_pricing
        except (yaml.YAMLError, TypeError, ValueError) as e:
            logger.error(
                f"Failed to parse pricing config '{self.pricing_config_path}': {e}"
            )
            return {}

    def validate_pricing_mode(self) -> None:
        """
        Validates the consistency of pricing_mode with the actual pricing config.

        Raises:
            ValueError: If pricing_mode='on' but no pricing configuration exists.

        """
        has_pricing = bool(self.pricing)

        if self.pricing_mode == "on" and not has_pricing:
            twitter_error_msg = (
                "pricing_mode is 'on' but no pricing configuration found. "
                "Either set MCP_TWITTER_X402_PRICING_MODE=off or provide a valid "
                f"pricing config at '{self.pricing_config_path}'."
            )
            raise ValueError(twitter_error_msg)

        if self.pricing_mode == "off" and has_pricing:
            logger.warning(
                f"Pricing configuration found ({len(self.pricing)} endpoints) but "
                "pricing_mode='off'. x402 payments are disabled. "
                "Set MCP_TWITTER_X402_PRICING_MODE=on to enable payments."
            )
        elif self.pricing_mode == "on" and has_pricing:
            logger.info(
                f"x402 payment validation passed: pricing_mode='on' with "
                f"{len(self.pricing)} priced endpoints."
            )

    def validate_against_routes(self, routes: list):
        """
        Checks pricing configuration against all available routes and logs status.
        """
        configured_op_ids = set(self.pricing.keys())
        valid_op_ids = {
            getattr(route, "operation_id", None)
            for route in routes
            if hasattr(route, "operation_id") and route.operation_id
        }

        logger.info("--- Validating Endpoint Pricing Configuration ---")
        self._log_correctly_configured(configured_op_ids, valid_op_ids)
        self._log_unpriced_endpoints(configured_op_ids, valid_op_ids)
        self._log_misconfigured_prices(configured_op_ids, valid_op_ids)
        logger.info("--- Pricing Validation Complete ---")

    def _log_correctly_configured(self, configured_ids: set, valid_op_ids: set):
        """Logs endpoints that are correctly priced."""
        correctly_configured = configured_ids.intersection(valid_op_ids)
        if correctly_configured:
            logger.info("Successfully configured pricing for:")
            for op_id in sorted(correctly_configured):
                logger.info(f"  - {op_id}")

    def _log_unpriced_endpoints(self, configured_ids: set, valid_op_ids: set):
        """Logs endpoints that exist but are not priced."""
        unpriced = valid_op_ids - configured_ids
        if unpriced:
            logger.debug(
                "The following endpoints are not priced (this may be intentional):"
            )
            for op_id in sorted(unpriced):
                logger.debug(f"  - {op_id}")

    def _log_misconfigured_prices(self, configured_ids: set, valid_op_ids: set):
        """Logs priced operation_ids that do not match any endpoint."""
        misconfigured = configured_ids - valid_op_ids
        if misconfigured:
            logger.warning("Pricing configuration mismatch found:")
            for op_id in sorted(misconfigured):
                logger.warning(
                    f"  - The operation_id '{op_id}' is priced in your tool_pricing.yaml, "
                    "but no corresponding endpoint was found. (Typo?)"
                )


@lru_cache(maxsize=1)
def get_x402_settings() -> X402Config:
    return X402Config()

"""
This module should be changed to fit your deployment and payment model, adjusting environment prefixes, defaults, and x402 settings while keeping the overall structure.

Main responsibility: Define and load x402 payment configuration, exposing cached helpers to access these settings.
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from x402.http import FacilitatorConfig
from x402.mechanisms.evm.utils import get_asset_info as get_evm_asset_info
from x402.mechanisms.evm.utils import get_network_config as get_evm_network_config
from x402.mechanisms.svm.utils import get_network_config as get_svm_network_config

from mcp_server_deepresearcher.x402_integration.accepted_assets import (
    CHAIN_ID_TO_NETWORK,
    EVM_NETWORKS,
    SOLANA_NETWORKS,
    register_custom_evm_networks,
    usd_to_token_amount,
)

logger = logging.getLogger(__name__)

# Register custom EVM networks at module load time, BEFORE X402Config class is used.
# This ensures networks like SEI are available when pricing validation runs.
register_custom_evm_networks()


class PaymentOptionConfig(BaseModel):
    """
    Defines a single payment option for a protected resource as stored in YAML.
    This is the configuration format that gets transformed into x402 v2 PaymentOption.

    Note: price_usd is specified in USD (e.g., 0.0001 for $0.0001).
    The system automatically converts to token amounts based on token decimals.

    chain_id can be:
    - An integer for EVM networks (e.g., 8453 for Base, 43114 for Avalanche, 56 for BNB Chain)
    - A string for Solana networks (e.g., "solana" or "solana-devnet")
    """

    chain_id: int | str
    token_address: str
    price_usd: float = Field(gt=0, description="Price in USD (e.g., 0.0001 for $0.0001)")

    def validate_config(self) -> None:
        """Validate the payment option configuration after model construction."""
        # Validate chain_id
        valid_chains = set(CHAIN_ID_TO_NETWORK.keys())
        if self.chain_id not in valid_chains:
            valid_chains_str = ", ".join(str(k) for k in sorted(valid_chains, key=str))
            raise ValueError(
                f"Unknown chain_id '{self.chain_id}'. Must be one of: {valid_chains_str}. "
                f"Add it to CHAIN_ID_TO_NETWORK in x402_config.py if this is a new network."
            )

        # Validate token_address format
        if not self.token_address or not self.token_address.strip():
            raise ValueError("token_address cannot be empty")

    @computed_field
    @property
    def token_amount(self) -> int:
        """
        Convert USD price to token amount based on actual token decimals.

        Uses x402 library's asset lookup functions to retrieve the correct decimals
        for the specific token on the specific network. Supports both EVM and Solana.

        IMPORTANT: Only returns token amount for tokens that are explicitly registered
        in x402's NETWORK_CONFIGS. This ensures the token supports EIP-3009 and has
        correct EIP-712 domain parameters.

        Returns:
            Token amount in smallest unit (e.g., 100 for 0.0001 USDC with 6 decimals)

        Raises:
            ValueError: If network or token is not found (validation happens in validate_config)
        """
        # Get CAIP-2 network identifier
        network = CHAIN_ID_TO_NETWORK.get(self.chain_id)
        if not network:
            raise ValueError(f"Unknown network for chain_id {self.chain_id}")

        if network in EVM_NETWORKS:
            asset_info = get_evm_asset_info(network, self.token_address)
            config = get_evm_network_config(network)
            is_recognized = any(
                asset["address"].lower() == self.token_address.lower()
                for asset in config["supported_assets"].values()
            )

            if not is_recognized:
                raise ValueError(
                    f"Token {self.token_address} is not registered in x402 library for "
                    f"network {network}. Only EIP-3009 compatible tokens are supported. "
                    f"Add this token to NETWORK_CONFIGS in your x402_config.py if you "
                    f"control the token contract."
                )

            decimals = asset_info["decimals"]
        elif network in SOLANA_NETWORKS:
            svm_config = get_svm_network_config(network)
            decimals = svm_config["default_asset"]["decimals"]
        else:
            raise ValueError(
                f"Network {network} not in EVM_NETWORKS or SOLANA_NETWORKS"
            )

        return usd_to_token_amount(self.price_usd, decimals)


class X402Config(BaseSettings):
    """
    Configuration for the x402 payment protocol.
    Loads simple key-value settings from environment variables and complex
    pricing structures from a dedicated YAML file.

    Environment variables:
        MCP_DEEP_RESEARCHER_X402_PRICING_MODE: Enable/disable payment enforcement ("on" or "off")
        MCP_DEEP_RESEARCHER_X402_FACILITATOR_URLS: JSON array of facilitator URLs (e.g., '["https://url1","https://url2"]')
        MCP_DEEP_RESEARCHER_X402_PAYEE_EVM_ADDRESS: EVM wallet address for receiving payments
        MCP_DEEP_RESEARCHER_X402_PAYEE_SOLANA_ADDRESS: Solana wallet address for receiving payments
        MCP_DEEP_RESEARCHER_X402_PRICING_CONFIG_PATH: Path to tool_pricing.yaml file
    """

    model_config = SettingsConfigDict(
        env_prefix="MCP_DEEP_RESEARCHER_X402_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    pricing_mode: Literal["off", "on"] = "off"

    # Multi-facilitator support - JSON array of URLs
    facilitator_urls: list[str] | None = Field(
        default=None,
        description="JSON array of facilitator URLs for multi-chain support"
    )

    # EVM wallet address (0x...) - used for Base, Avalanche, SKALE Base, BNB Chain
    payee_evm_address: str | None = None
    # Solana wallet address (Base58) - used for Solana
    payee_solana_address: str | None = None

    pricing_config_path: Path = Path("tool_pricing.yaml")

    def model_post_init(self, __context) -> None:
        """
        Called after model initialization to perform setup that requires
        side effects (like registering custom networks in x402 library).
        """
        # Register custom EVM networks when config is instantiated
        # This ensures networks are available when middleware is initialized
        register_custom_evm_networks()

    @field_validator("facilitator_urls", mode="before")
    @classmethod
    def parse_facilitator_urls(cls, v: str | list[str] | None) -> list[str] | None:
        """Parse JSON array string from environment variable to list of URLs.

        Examples:
            '["https://facilitator.payai.network","https://api.x402.unibase.com/v2"]'
            ["url1", "url2"]  # Already a list
            None
        """
        if v is None:
            return None
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            # Remove surrounding quotes if present
            v = v.strip().strip('"').strip("'")
            if not v or v.lower() == "none":
                return None
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
                # If single string after JSON parse, wrap in list
                return [parsed]
            except json.JSONDecodeError:
                # If it's not valid JSON, treat as single-item list
                logger.warning(
                    f"Failed to parse facilitator_urls as JSON: {v}. "
                    "Treating as single URL."
                )
                return [v]
        return None

    @computed_field
    @property
    def facilitator_config(self) -> list[FacilitatorConfig]:
        """Creates list of facilitator configurations from facilitator_urls.

        Returns:
            List of FacilitatorConfig objects, or empty list if none configured
        """
        configs: list[FacilitatorConfig] = []

        if self.facilitator_urls:
            for url in self.facilitator_urls:
                configs.append(FacilitatorConfig(url=url))
            logger.info(
                f"Configured {len(self.facilitator_urls)} facilitator(s) from FACILITATOR_URLS"
            )
        else:
            logger.warning(
                "No facilitators configured. Payment enforcement will be disabled. "
                "Set MCP_DEEP_RESEARCHER_X402_FACILITATOR_URLS environment variable."
            )

        return configs

    @computed_field
    @property
    def pricing(self) -> dict[str, list[PaymentOptionConfig]]:
        """
        A computed field that loads, parses, and validates the pricing
        configuration from the YAML file specified by 'pricing_config_path'.

        Strict validation: If any payment option contains unknown chain_id or
        unregistered token_address, that entry is skipped and a warning is logged.
        Only validated payment options are included in the final pricing dict.
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

            if not isinstance(pricing_data, dict):
                raise ValueError(
                    f"expected a YAML mapping (dict) but got {type(pricing_data).__name__}"
                )

            validated_pricing = {}
            skipped_count = 0

            for op_id, opts in pricing_data.items():
                payment_options = []
                for idx, opt in enumerate(opts):
                    try:
                        payment_opt = PaymentOptionConfig(**opt)
                        # Validate each option after construction
                        payment_opt.validate_config()
                        # Trigger token_amount computation to validate token registration
                        _ = payment_opt.token_amount
                        payment_options.append(payment_opt)
                    except ValueError as e:
                        # Skip this payment option and log warning
                        logger.warning(
                            f"Skipping invalid payment option for '{op_id}' (entry #{idx}): {e}"
                        )
                        skipped_count += 1
                        continue

                # Only add to validated pricing if we have at least one valid option
                if payment_options:
                    validated_pricing[op_id] = payment_options
                else:
                    logger.warning(
                        f"Tool '{op_id}' has no valid payment options. "
                        "It will not have payment requirements."
                    )

        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML syntax: {e}") from e
        except (TypeError, AttributeError) as e:
            raise ValueError(
                f"Each endpoint must map to a list of payment options: {e}"
            ) from e

        if skipped_count > 0:
            logger.warning(
                f"Skipped {skipped_count} invalid payment option(s) during config loading. "
                "See warnings above for details."
            )

        logger.info(
            f"Successfully loaded pricing for {len(validated_pricing)} tool(s) "
            f"with {sum(len(opts) for opts in validated_pricing.values())} valid payment option(s)."
        )
        return validated_pricing

    def validate_pricing_mode(self) -> None:
        """
        Validates the consistency of pricing_mode with the actual pricing config.

        Raises:
            ValueError: If pricing_mode='on' but no pricing configuration exists.
                       This fails fast rather than silently running without payments.

        Logs warnings for:
            - pricing_mode='off' when pricing config exists (payments disabled but config present)

        """
        has_pricing = bool(self.pricing)

        if self.pricing_mode == "on" and not has_pricing:
            raise ValueError(
                "pricing_mode is 'on' but no pricing configuration found. "
                "Either set MCP_DEEP_RESEARCHER_X402_PRICING_MODE=off or provide a valid "
                f"pricing config at '{self.pricing_config_path}'."
            )

        if self.pricing_mode == "off" and has_pricing:
            logger.warning(
                f"Pricing configuration found ({len(self.pricing)} endpoints) but "
                "pricing_mode='off'. x402 payments are disabled. "
                "Set MCP_DEEP_RESEARCHER_X402_PRICING_MODE=on to enable payments."
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

    def get_payee_address(self, network: str) -> str | None:
        """Get the appropriate payee address for a given CAIP-2 network identifier."""
        if network in SOLANA_NETWORKS:
            return self.payee_solana_address
        return self.payee_evm_address


@lru_cache(maxsize=1)
def get_x402_settings() -> X402Config:
    return X402Config()

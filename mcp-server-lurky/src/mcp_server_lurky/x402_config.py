"""
x402 payment protocol configuration module.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict
from x402.http import AuthHeaders, FacilitatorConfig
from x402.mechanisms.evm.utils import NETWORK_CONFIGS

logger = logging.getLogger(__name__)


def _register_custom_evm_networks() -> None:
    """Register custom EVM networks not yet in x402 library."""
    # SKALE Base (L3 on Base) - launched Jan 2026
    # Docs: https://docs.skale.space/welcome/skale-on-base
    if "eip155:1187947933" not in NETWORK_CONFIGS:
        NETWORK_CONFIGS["eip155:1187947933"] = {
            "chain_id": 1187947933,
            "default_asset": {
                "address": "0x85889c8c714505E0c94b30fcfcF64fE3Ac8FCb20",
                "name": "Bridged USDC (SKALE Bridge)",  # Must match Kobaru's expected name
                "version": "2",
                "decimals": 6,
            },
            "supported_assets": {
                "USDC": {
                    "address": "0x85889c8c714505E0c94b30fcfcF64fE3Ac8FCb20",
                    "name": "Bridged USDC (SKALE Bridge)",  # Must match Kobaru's expected name
                    "version": "2",
                    "decimals": 6,
                },
            },
        }
        logger.info("Registered custom EVM network: SKALE Base (eip155:1187947933)")


# Register custom networks at module load time
_register_custom_evm_networks()

# Mapping from chain_id to CAIP-2 network identifier
# See: https://chainagnostic.org/CAIPs/caip-2
CHAIN_ID_TO_NETWORK: dict[int, str] = {
    1: "eip155:1",  # Ethereum Mainnet
    8453: "eip155:8453",  # Base Mainnet
    84532: "eip155:84532",  # Base Sepolia
    10: "eip155:10",  # Optimism
    42161: "eip155:42161",  # Arbitrum One
    137: "eip155:137",  # Polygon
    43114: "eip155:43114",  # Avalanche C-Chain
    1187947933: "eip155:1187947933",  # SKALE Base (L3 on Base)
}

# Load environment variables from the repo-root .env file (if present).
_project_root = Path(__file__).resolve().parents[2]
_env_file = _project_root / ".env"


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
    """

    model_config = SettingsConfigDict(
        env_prefix="MCP_LURKY_X402_",
        env_file=_env_file,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    pricing_mode: Literal["off", "on"] = "off"
    payee_wallet_address: str | None = None
    facilitator_url: str | None = "https://x402-facilitator.kobaru.xyz/v2"
    cdp_api_key_id: str | None = None
    cdp_api_key_secret: str | None = None

    pricing_config_path: Path = Path("tool_pricing.yaml")

    @computed_field
    @property
    def facilitator_config(self) -> FacilitatorConfig | None:
        """
        A computed field that creates the correct facilitator configuration.
        - If CDP API keys are present, it configures for mainnet CDP facilitator.
        - If a facilitator_url is provided, it configures for that URL.
        - If neither is provided, returns None, disabling payments.
        """
        if self.cdp_api_key_id and self.cdp_api_key_secret:
            # CDP mainnet facilitator with API key authentication
            # See: https://docs.cdp.coinbase.com/x402/docs/facilitator
            logger.info("CDP API keys found, configuring for mainnet facilitator.")
            try:
                from cdp.auth.utils.http import GetAuthHeadersOptions, get_auth_headers
                from cdp.x402.x402 import (
                    COINBASE_FACILITATOR_BASE_URL,
                    COINBASE_FACILITATOR_V2_ROUTE,
                    X402_VERSION,
                )

                api_key_id = self.cdp_api_key_id
                api_key_secret = self.cdp_api_key_secret
                request_host = COINBASE_FACILITATOR_BASE_URL.replace("https://", "")

                class CDPAuthProvider:
                    """AuthProvider that generates JWT auth for CDP facilitator."""

                    def get_auth_headers(self) -> AuthHeaders:
                        """Generate auth headers for CDP facilitator endpoints."""
                        verify_headers = get_auth_headers(
                            GetAuthHeadersOptions(
                                api_key_id=api_key_id,
                                api_key_secret=api_key_secret,
                                request_host=request_host,
                                request_path=f"{COINBASE_FACILITATOR_V2_ROUTE}/verify",
                                request_method="POST",
                                source="x402",
                                source_version=X402_VERSION,
                            )
                        )
                        settle_headers = get_auth_headers(
                            GetAuthHeadersOptions(
                                api_key_id=api_key_id,
                                api_key_secret=api_key_secret,
                                request_host=request_host,
                                request_path=f"{COINBASE_FACILITATOR_V2_ROUTE}/settle",
                                request_method="POST",
                                source="x402",
                                source_version=X402_VERSION,
                            )
                        )
                        # CDP requires auth for /supported endpoint too (despite SDK comment)
                        supported_headers = get_auth_headers(
                            GetAuthHeadersOptions(
                                api_key_id=api_key_id,
                                api_key_secret=api_key_secret,
                                request_host=request_host,
                                request_path=f"{COINBASE_FACILITATOR_V2_ROUTE}/supported",
                                request_method="GET",
                                source="x402",
                                source_version=X402_VERSION,
                            )
                        )
                        return AuthHeaders(
                            verify=verify_headers,
                            settle=settle_headers,
                            supported=supported_headers,
                        )

                facilitator_url = (
                    f"{COINBASE_FACILITATOR_BASE_URL}{COINBASE_FACILITATOR_V2_ROUTE}"
                )
                return FacilitatorConfig(
                    url=facilitator_url,
                    auth_provider=CDPAuthProvider(),
                )
            except ImportError:
                logger.warning(
                    "cdp-sdk not installed but CDP keys provided. "
                    "Install cdp-sdk or use facilitator_url instead."
                )
                return None
        if self.facilitator_url:
            logger.info(f"Using public facilitator at {self.facilitator_url}")
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

            if not isinstance(pricing_data, dict):
                raise ValueError(
                    f"expected a YAML mapping (dict) but got {type(pricing_data).__name__}"
                )

            validated_pricing = {
                op_id: [PaymentOptionConfig(**opt) for opt in opts]
                for op_id, opts in pricing_data.items()
            }

        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML syntax: {e}") from e
        except (TypeError, AttributeError) as e:
            raise ValueError(
                f"Each endpoint must map to a list of payment options: {e}"
            ) from e
        except ValueError:
            raise

        logger.info(f"Successfully loaded pricing for {len(validated_pricing)} tools.")
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
                "Either set MCP_LURKY_X402_PRICING_MODE=off or provide a valid "
                f"pricing config at '{self.pricing_config_path}'."
            )

        if self.pricing_mode == "off" and has_pricing:
            logger.warning(
                f"Pricing configuration found ({len(self.pricing)} endpoints) but "
                "pricing_mode='off'. x402 payments are disabled. "
                "Set MCP_LURKY_X402_PRICING_MODE=on to enable payments."
            )
        elif self.pricing_mode == "on" and has_pricing:
            logger.info(
                f"x402 payment validation passed: pricing_mode='on' with "
                f"{len(self.pricing)} priced endpoints."
            )

    def validate_against_routes(self, routes: list):
        configured_op_ids = set(self.pricing.keys())
        valid_op_ids = {
            getattr(route, "operation_id", None)
            for route in routes
            if hasattr(route, "operation_id") and route.operation_id
        }
        logger.info(f"Priced: {configured_op_ids}, Routes: {valid_op_ids}")


@lru_cache(maxsize=1)
def get_x402_settings() -> X402Config:
    return X402Config()

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

CHAIN_ID_TO_NETWORK: dict[int, str] = {
    1: "eip155:1",
    8453: "eip155:8453",
    84532: "eip155:84532",
    10: "eip155:10",
    42161: "eip155:42161",
    137: "eip155:137",
}


class PaymentOptionConfig(BaseModel):
    chain_id: int
    token_address: str
    token_amount: int = Field(ge=0)


class X402Config(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="MCP_TELEGRAM_X402_",
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
        if self.cdp_api_key_id and self.cdp_api_key_secret:
            logger.info("CDP API keys found, configuring for mainnet facilitator.")
            try:
                from cdp.x402 import create_facilitator_config

                return create_facilitator_config(
                    api_key_id=self.cdp_api_key_id,
                    api_key_secret=self.cdp_api_key_secret,
                )
            except ImportError:
                logger.warning("CDP SDK not available.")
                return None
        if self.facilitator_url:
            logger.info(f"Using public facilitator at {self.facilitator_url}")
            from x402.http import FacilitatorConfig

            return FacilitatorConfig(url=self.facilitator_url)
        return None

    @computed_field
    @property
    def pricing(self) -> dict[str, list[PaymentOptionConfig]]:
        if not self.pricing_config_path.is_file():
            logger.warning(f"Pricing config not found at '{self.pricing_config_path}'.")
            return {}
        try:
            with open(self.pricing_config_path) as f:
                pricing_data = yaml.safe_load(f)
                if not pricing_data:
                    return {}
                validated_pricing = {
                    op_id: [PaymentOptionConfig(**opt) for opt in opts]
                    for op_id, opts in pricing_data.items()
                }
                logger.info(f"Loaded pricing for {len(validated_pricing)} tools.")
                return validated_pricing
        except (yaml.YAMLError, TypeError, ValueError) as e:
            logger.error(f"Failed to parse pricing config: {e}")
            return {}

    def validate_pricing_mode(self) -> None:
        has_pricing = bool(self.pricing)
        if self.pricing_mode == "on" and not has_pricing:
            raise ValueError(
                "pricing_mode is 'on' but no pricing configuration found. "
                "Either set MCP_TELEGRAM_X402_PRICING_MODE=off or provide a valid "
                f"pricing config at '{self.pricing_config_path}'."
            )
        if self.pricing_mode == "off" and has_pricing:
            logger.warning(
                f"Pricing config found ({len(self.pricing)} endpoints) but pricing_mode='off'."
            )
        elif self.pricing_mode == "on" and has_pricing:
            logger.info(
                f"x402 validation passed: {len(self.pricing)} priced endpoints."
            )


@lru_cache(maxsize=1)
def get_x402_settings() -> X402Config:
    return X402Config()

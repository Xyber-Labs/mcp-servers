from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml
from cdp.x402 import create_facilitator_config
from pydantic import BaseModel, Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict
from x402.facilitator import FacilitatorConfig

logger = logging.getLogger(__name__)


class PaymentOption(BaseModel):
    chain_id: int
    token_address: str
    token_amount: int = Field(ge=0)


class X402Config(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="MCP_TAVILY_X402_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    pricing_mode: Literal["off", "on"] = "on"
    payee_wallet_address: str | None = None
    facilitator_url: str | None = None
    cdp_api_key_id: str | None = None
    cdp_api_key_secret: str | None = None

    pricing_config_path: Path = Path("tool_pricing.yaml")

    @computed_field
    @property
    def facilitator_config(self) -> FacilitatorConfig | None:
        if self.cdp_api_key_id and self.cdp_api_key_secret:
            logger.info("CDP API keys found, configuring for mainnet facilitator.")
            return create_facilitator_config(
                api_key_id=self.cdp_api_key_id,
                api_key_secret=self.cdp_api_key_secret,
            )
        if self.facilitator_url:
            logger.info(f"Using public facilitator at {self.facilitator_url}")
            return {"url": self.facilitator_url}
        return None

    @computed_field
    @property
    def pricing(self) -> dict[str, list[PaymentOption]]:
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
                validated_pricing = {
                    op_id: [PaymentOption(**opt) for opt in opts]
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

    def validate_against_routes(self, routes: list):
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
        correctly_configured = configured_ids.intersection(valid_op_ids)
        if correctly_configured:
            logger.info("Successfully configured pricing for:")
            for op_id in sorted(correctly_configured):
                logger.info(f"  - {op_id}")

    def _log_unpriced_endpoints(self, configured_ids: set, valid_op_ids: set):
        unpriced = valid_op_ids - configured_ids
        if unpriced:
            logger.debug(
                "The following endpoints are not priced (this may be intentional):"
            )
            for op_id in sorted(unpriced):
                logger.debug(f"  - {op_id}")

    def _log_misconfigured_prices(self, configured_ids: set, valid_op_ids: set):
        misconfigured = configured_ids - valid_op_ids
        if misconfigured:
            logger.warning("Pricing configuration mismatch found:")
            for op_id in sorted(misconfigured):
                logger.warning(
                    f"  - The operation_id '{op_id}' is priced in your tool_pricing.yaml, "
                    "but no corresponding endpoint was found. (Typo?)"
                )


class AppSettings(BaseSettings):
    host: str = "0.0.0.0"
    port: int = 8005
    logging_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    hot_reload: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="MCP_TAVILY_",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_app_settings() -> AppSettings:
    return AppSettings()


@lru_cache(maxsize=1)
def get_x402_settings() -> X402Config:
    return X402Config()


"""
Configuration module for the MCP Twitter scraper CLI.

Loads `.env` from repo root when running from source checkout.
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml
from cdp.x402 import create_facilitator_config
from dotenv import load_dotenv
from pydantic import BaseModel, Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict
from x402.facilitator import FacilitatorConfig

import logging

logger = logging.getLogger(__name__)


# Load environment variables from the repo-root .env file (if present).
# File location: <repo>/src/mcp_twitter/config.py -> repo root is 2 levels up.
_project_root = Path(__file__).resolve().parents[2]
_env_file = _project_root / ".env"
load_dotenv(dotenv_path=_env_file)


class ApifyConfig(BaseModel):
    """Apify API configuration."""

    # Prefer the common `APIFY_TOKEN`, but allow nested form too.
    apify_token: str | None = os.getenv("APIFY_TOKEN") or os.getenv(
        "MCP_TWITTER__APIFY__APIFY_TOKEN"
    )
    
    # Actor name can be set via APIFY_ACTOR_NAME or MCP_TWITTER__APIFY__ACTOR_NAME
    actor_name: str = os.getenv("APIFY_ACTOR_NAME") or os.getenv(
        "MCP_TWITTER__APIFY__ACTOR_NAME",
        "apidojo/twitter-scraper-lite",  # Default fallback
    )


class DatabaseConfig(BaseModel):
    """Database configuration for Postgres cache."""

    DB_NAME: str = os.getenv("DB_NAME", "mcp_twitter_apify")
    DB_USER: str = os.getenv("DB_USER", "postgres")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "postgres")
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT_RAW: str = os.getenv("DB_PORT", "5432")
    DB_PORT: str = (
        DB_PORT_RAW.split(":")[0] if ":" in DB_PORT_RAW else DB_PORT_RAW
    )
    DATABASE_URL: str = (
        f"postgresql+psycopg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )
    logger.info(f"DEBUG: Connecting to: {DATABASE_URL}")

    # Cache TTL defaults (in seconds)
    cache_ttl_topic_latest: int = int(os.getenv("CACHE_TTL_TOPIC_LATEST", "900"))  # 15 min
    cache_ttl_topic_top: int = int(os.getenv("CACHE_TTL_TOPIC_TOP", "86400"))  # 24 hours
    cache_ttl_profile: int = int(os.getenv("CACHE_TTL_PROFILE", "1800"))  # 30 min
    cache_ttl_replies: int = int(os.getenv("CACHE_TTL_REPLIES", "3600"))  # 1 hour


class PaymentOption(BaseModel):
    """
    Defines a single payment option for a protected resource, aligning with the
    data needed to construct an `x402.types.PaymentRequirements` object.

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
        env_file=_env_file,
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
        """
        A computed field that creates the correct facilitator configuration.
        - If CDP API keys are present, it configures for mainnet.
        - If a facilitator_url is provided, it configures for that URL.
        - If neither is provided, returns None, disabling payments.
        """
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
                    f"  - The operation_id '{op_id}' is priced in your .env file, "
                    "but no corresponding endpoint was found. (Typo?)"
                )


class AppSettings(BaseSettings):
    """Application settings for the MCP Twitter scraper CLI."""

    host: str = "0.0.0.0"
    port: int = 8002
    logging_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    hot_reload: bool = False

    apify: ApifyConfig = ApifyConfig()
    database: DatabaseConfig = DatabaseConfig()

    model_config = SettingsConfigDict(
        env_file=_env_file,
        env_file_encoding="utf-8",
        env_prefix="MCP_TWITTER_",
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


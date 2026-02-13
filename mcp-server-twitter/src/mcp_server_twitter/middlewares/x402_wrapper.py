"""
Payment-enforcing middleware that applies x402 pricing to REST and MCP calls.
Updated for x402 v2.0.0 with CAIP-2 network identifiers and new API structure.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import httpx
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.routing import Match
from x402.http import (
    PAYMENT_REQUIRED_HEADER,
    HTTPFacilitatorClient,
    encode_payment_required_header,
    safe_base64_decode,
    safe_base64_encode,
)
from x402.mechanisms.evm.exact import ExactEvmServerScheme
from x402.schemas import Network, PaymentPayload, PaymentRequired, PaymentRequirements
from x402.server import x402ResourceServer

from mcp_server_twitter.x402_config import (
    CHAIN_ID_TO_NETWORK,
    PaymentOptionConfig,
    X402Config,
    get_x402_settings,
)

logger = logging.getLogger(__name__)

# CAIP-2 network -> block explorer base URL (for observable transactions)
_EXPLORER_BASE: dict[str, str] = {
    "eip155:1": "https://etherscan.io",
    "eip155:8453": "https://basescan.org",
    "eip155:84532": "https://sepolia.basescan.org",
    "eip155:10": "https://optimistic.etherscan.io",
    "eip155:42161": "https://arbiscan.io",
    "eip155:137": "https://polygonscan.com",
}


def _explorer_tx_url(network: Network, tx_hash: str) -> str:
    """Build block explorer tx URL for a given CAIP-2 network and tx hash."""
    base = _EXPLORER_BASE.get(str(network), "")
    if not base or not tx_hash:
        return ""
    return f"{base}/tx/{tx_hash}"


class X402WrapperMiddleware(BaseHTTPMiddleware):
    """
    Payment middleware for x402 v2 protocol.
    Handles MCP-aware pricing and multiple payment options per endpoint.
    """

    FACILITATOR_VERIFY_MAX_RETRIES = 5
    FACILITATOR_VERIFY_RETRY_DELAY_SECONDS = 1.0

    PAYMENT_HEADER = "PAYMENT-SIGNATURE"
    PAYMENT_RESPONSE_HEADER = "PAYMENT-RESPONSE"
    LEGACY_PAYMENT_HEADER = "X-PAYMENT"

    def __init__(self, app, tool_pricing: dict[str, list[PaymentOptionConfig]]):
        super().__init__(app)
        self.tool_pricing = tool_pricing
        self.settings: X402Config = get_x402_settings()
        self.facilitator: HTTPFacilitatorClient | None = None
        self.server: x402ResourceServer | None = None

        if facilitator_config := self.settings.facilitator_config:
            self.facilitator = HTTPFacilitatorClient(facilitator_config)
            self.server = x402ResourceServer(self.facilitator)
            self.server.initialize()
            self._register_evm_schemes()
        else:
            logger.warning(
                "No x402 facilitator configured. Payment middleware disabled."
            )

    def _register_evm_schemes(self) -> None:
        """Register EVM scheme for all networks used in pricing config."""
        if not self.server:
            return
        networks_used: set[str] = set()
        for options in self.tool_pricing.values():
            for opt in options:
                if network := CHAIN_ID_TO_NETWORK.get(opt.chain_id):
                    networks_used.add(network)
                else:
                    logger.warning(
                        f"Unknown chain_id '{opt.chain_id}' in pricing config."
                    )
        for network in networks_used:
            self.server.register(network, ExactEvmServerScheme())
            logger.info(f"Registered EVM scheme for network: {network}")

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if not self.facilitator or not self.server:
            return await call_next(request)

        operation_id = await self._get_operation_id(request)
        pricing_options = self.tool_pricing.get(operation_id) if operation_id else None

        if not operation_id or not pricing_options:
            return await call_next(request)

        payment_requirements = self._build_payment_requirements(
            pricing_options, request
        )

        payment_header = request.headers.get(
            self.PAYMENT_HEADER
        ) or request.headers.get(self.LEGACY_PAYMENT_HEADER)

        if not payment_header:
            logger.warning(f"Payment header missing for '{operation_id}'")
            return self._create_402_response(
                payment_requirements, "No payment header provided"
            )

        try:
            payment_dict = json.loads(safe_base64_decode(payment_header))
            payment = PaymentPayload(**payment_dict)
        except Exception as e:
            client_host = request.client.host if request.client else "<unknown>"
            logger.warning(f"Invalid payment header from {client_host}: {e}")
            return self._create_402_response(
                payment_requirements, "Invalid payment header format"
            )

        selected_req = self._find_matching_requirement(payment_requirements, payment)
        if not selected_req:
            return self._create_402_response(
                payment_requirements, "No matching payment requirements found"
            )

        try:
            verify_response = await self._verify_with_retry(
                payment,
                selected_req,
                max_retries=self.FACILITATOR_VERIFY_MAX_RETRIES,
                retry_delay_seconds=self.FACILITATOR_VERIFY_RETRY_DELAY_SECONDS,
            )
        except httpx.HTTPError as exc:
            logger.error(
                "Payment verification failed after %d attempts for '%s': %s",
                self.FACILITATOR_VERIFY_MAX_RETRIES,
                operation_id,
                exc,
            )
            return self._create_402_response(
                payment_requirements,
                "Payment verification failed; please try again later.",
            )

        if not verify_response.is_valid:
            reason = verify_response.invalid_reason or "Unknown reason"
            return self._create_402_response(
                payment_requirements, f"Invalid payment: {reason}"
            )

        response = await call_next(request)

        if 200 <= response.status_code < 300:
            try:
                settle_response = await self.server.settle_payment(
                    payment, selected_req
                )
                if settle_response.success:
                    response.headers[self.PAYMENT_RESPONSE_HEADER] = safe_base64_encode(
                        settle_response.model_dump_json(by_alias=True)
                    )
                    tx_hash = getattr(settle_response, "transaction", None) or ""
                    network = getattr(settle_response, "network", None) or ""
                    if tx_hash:
                        explorer_url = _explorer_tx_url(network, tx_hash)
                        logger.info(
                            "Payment settled: tx=%s network=%s%s",
                            tx_hash,
                            network,
                            f" | {explorer_url}" if explorer_url else "",
                        )
                else:
                    reason = settle_response.error_reason or "Unknown"
                    logger.error(
                        f"Payment settlement failed for '{operation_id}': {reason}"
                    )
            except Exception as e:
                logger.error(f"Exception during settlement for '{operation_id}': {e}")

        return response

    async def _verify_with_retry(
        self,
        payment: PaymentPayload,
        payment_requirements: PaymentRequirements,
        max_retries: int = 5,
        retry_delay_seconds: float = 1.0,
    ) -> Any:
        """Verify payment with exponential backoff retry."""
        last_error: httpx.HTTPError | None = None
        for attempt in range(1, max_retries + 1):
            try:
                return await self.server.verify_payment(payment, payment_requirements)
            except httpx.HTTPError as exc:
                last_error = exc
                logger.warning(
                    "Facilitator verify attempt %d/%d failed: %s",
                    attempt,
                    max_retries,
                    exc,
                )
                if attempt < max_retries:
                    delay = retry_delay_seconds * (2 ** (attempt - 1))
                    logger.info(
                        "Retrying payment verification in %.1f seconds...", delay
                    )
                    await asyncio.sleep(delay)
        assert last_error is not None
        raise last_error

    def _create_402_response(
        self, requirements: list[PaymentRequirements], error: str
    ) -> JSONResponse:
        """Constructs a 402 Payment Required response."""
        payment_required = PaymentRequired(
            x402_version=2,
            error=error,
            accepts=requirements,
        )

        response_data = {
            "x402Version": 2,
            "accepts": [req.model_dump(by_alias=True) for req in requirements],
            "error": error,
        }

        response = JSONResponse(content=response_data, status_code=402)
        response.headers[PAYMENT_REQUIRED_HEADER] = encode_payment_required_header(
            payment_required
        )
        return response

    async def _get_operation_id(self, request: Request) -> str | None:
        """Determines the operation_id from the request."""
        path = request.url.path
        if path.startswith("/api/") or path.startswith("/hybrid/"):
            for route in request.app.routes:
                match, _ = route.matches(request.scope)
                if match != Match.NONE and hasattr(route, "operation_id"):
                    return route.operation_id
        elif "mcp" in path and request.method == "POST":
            try:
                body = await request.json()
                return (body.get("params") or {}).get("name")
            except json.JSONDecodeError:
                logger.warning("Could not decode JSON body for MCP request.")
                return None
        return None

    def _build_payment_requirements(
        self, options: list[PaymentOptionConfig], request: Request
    ) -> list[PaymentRequirements]:
        """Constructs payment requirements from config."""
        accepts: list[PaymentRequirements] = []
        for option in options:
            network: Network | None = CHAIN_ID_TO_NETWORK.get(option.chain_id)
            if not network:
                logger.warning(
                    f"Unknown chain_id '{option.chain_id}' in pricing config."
                )
                continue

            base_req = PaymentRequirements(
                scheme="exact",
                network=network,
                asset=option.token_address,
                amount=str(option.token_amount),
                pay_to=self.settings.payee_evm_address,
                max_timeout_seconds=60,
                extra={},
            )

            if self.server:
                schemes = self.server._schemes.get(network, {})
                scheme = schemes.get("exact")
                if scheme:
                    supported = self.server._supported_responses.get(network, {}).get(
                        "exact"
                    )
                    if supported:
                        supported_kind = None
                        for kind in supported.kinds:
                            if kind.scheme == "exact" and kind.network == network:
                                supported_kind = kind
                                break
                        if supported_kind:
                            base_req = scheme.enhance_payment_requirements(
                                base_req, supported_kind, []
                            )

            accepts.append(base_req)
        return accepts

    def _find_matching_requirement(
        self, requirements: list[PaymentRequirements], payment: PaymentPayload
    ) -> PaymentRequirements | None:
        """Find a requirement that matches the payment."""
        accepted = payment.accepted
        for req in requirements:
            if req.network == accepted.network and req.scheme == accepted.scheme:
                return req
        return None

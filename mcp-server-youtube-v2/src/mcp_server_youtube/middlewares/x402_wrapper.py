"""
This module will stay as is for most MCP servers, unless you need to customize how x402 payments are enforced or how headers and errors are handled.
Note: in future we will likely use x402 library directly, currently it misses some crucial features like:
- mcp endpoints pricing
- multiple payment options for a single endpoint

Main responsibility: Implement a payment-enforcing middleware that applies x402 pricing to REST and MCP calls based on configured tool pricing and a facilitator client.

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
from x402.mechanisms.svm.exact import ExactSvmServerScheme
from x402.schemas import Network, PaymentPayload, PaymentRequired, PaymentRequirements
from x402.server import x402ResourceServer

from mcp_server_youtube.x402_integration import (
    CHAIN_ID_TO_NETWORK,
    EVM_NETWORKS,
    SOLANA_NETWORKS,
    get_x402_settings,
)
from mcp_server_youtube.x402_integration.accepted_assets import CUSTOM_NETWORKS
from mcp_server_youtube.x402_integration.config import PaymentOptionConfig, X402Config

logger = logging.getLogger(__name__)


class X402WrapperMiddleware(BaseHTTPMiddleware):
    """
    A sophisticated wrapper that provides two key features on top of x402:
    1.  **Method-Aware MCP Pricing**: It inspects the JSON-RPC body of /mcp
        requests to determine the specific tool being called and applies the
        correct price.
    2.  **Multiple Payment Options**: It allows configuring multiple payment
        options (e.g., different tokens or networks) for a single endpoint.
    It achieves this by dynamically constructing the `PaymentRequirements` list
    based on the incoming request before processing the payment flow.

    Updated for x402 v2.0.0 with CAIP-2 network identifiers.
    """

    FACILITATOR_VERIFY_MAX_RETRIES = 5
    FACILITATOR_VERIFY_RETRY_DELAY_SECONDS = 1.0

    # v2 uses PAYMENT-SIGNATURE header instead of X-PAYMENT
    PAYMENT_HEADER = "PAYMENT-SIGNATURE"
    PAYMENT_RESPONSE_HEADER = "PAYMENT-RESPONSE"
    # Also support legacy header for backward compatibility
    LEGACY_PAYMENT_HEADER = "X-PAYMENT"

    def __init__(self, app, tool_pricing: dict[str, list[PaymentOptionConfig]]):
        super().__init__(app)
        self.tool_pricing = tool_pricing
        self.settings: X402Config = get_x402_settings()
        self.facilitators: list[HTTPFacilitatorClient] = []
        self.server: x402ResourceServer | None = None

        facilitator_configs = self.settings.facilitator_config
        if facilitator_configs:
            # Create client for each facilitator
            self.facilitators = [
                HTTPFacilitatorClient(config)
                for config in facilitator_configs
            ]

            # Pass all clients to server (SDK handles routing by chain)
            self.server = x402ResourceServer(self.facilitators)

            # Initialize server (queries all facilitators for supported chains)
            self.server.initialize()

            logger.info(f"Initialized x402 with {len(self.facilitators)} facilitator(s):")
            for client in self.facilitators:
                logger.info(f"  - {client._url}")
            # Register schemes for all configured networks AFTER initialize
            self._register_network_schemes()
        else:
            logger.warning(
                "No x402 facilitator configured (missing CDP keys and URL). "
                "Payment middleware will be disabled."
            )

    def _register_network_schemes(self) -> None:
        """Register appropriate schemes (EVM or Solana) for all networks in pricing config."""
        if not self.server:
            return
        networks_used: set[str] = set()
        for options in self.tool_pricing.values():
            for opt in options:
                if network := CHAIN_ID_TO_NETWORK.get(opt.chain_id):
                    networks_used.add(network)
                else:
                    logger.warning(
                        f"Unknown chain_id '{opt.chain_id}' in pricing config. "
                        f"Add it to CHAIN_ID_TO_NETWORK mapping in x402_config.py"
                    )

        for network in networks_used:
            if network in EVM_NETWORKS:
                self.server.register(network, ExactEvmServerScheme())
                logger.info(f"Registered EVM scheme for network: {network}")
            elif network in SOLANA_NETWORKS:
                self.server.register(network, ExactSvmServerScheme())
                logger.info(f"Registered Solana scheme for network: {network}")
            else:
                logger.warning(
                    f"Network '{network}' not in EVM_NETWORKS or SOLANA_NETWORKS. "
                    f"Update x402_config.py to classify this network."
                )

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if not self.facilitators or not self.server:
            return await call_next(request)

        operation_id = await self._get_operation_id(request)
        pricing_options = self.tool_pricing.get(operation_id) if operation_id else None

        if not operation_id or not pricing_options:
            return await call_next(request)

        payment_requirements = self._build_payment_requirements(
            pricing_options, request
        )

        # Check for payment header (v2 or legacy)
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
            payment_dict["resource"] = {
                "url": str(request.url),
                "description": "API access",
                "mimeType": "application/json",
            }
            payment = PaymentPayload(**payment_dict)
        except Exception as e:
            client_host = request.client.host if request.client else "<unknown>"
            logger.warning(f"Invalid payment header from {client_host}: {e}")
            return self._create_402_response(
                payment_requirements, "Invalid payment header format"
            )

        # In v2, the payment already contains the accepted requirement
        # We need to find the matching requirement from our list
        selected_req: PaymentRequirements = self._find_matching_requirement(payment_requirements, payment)
        if not selected_req:
            return self._create_402_response(
                payment_requirements, "No matching payment requirements found"
            )

        try:
            # Debug: log payment details being sent to facilitator
            logger.info(
                "Verifying payment: network=%s scheme=%s amount=%s payTo=%s",
                selected_req.network,
                selected_req.scheme,
                selected_req.amount,
                selected_req.pay_to,
            )
            logger.debug("Payment payload: %s", payment.model_dump_json(by_alias=True))
            logger.debug("Requirements: %s", selected_req.model_dump_json(by_alias=True))

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
        except ValueError as exc:
            # Facilitator returned an error (e.g., 500)
            logger.error(
                "Facilitator error for '%s': %s. Payment: %s",
                operation_id,
                exc,
                payment.model_dump_json(by_alias=True),
            )
            return self._create_402_response(
                payment_requirements,
                f"Facilitator error: {exc}",
            )

        if not verify_response.is_valid:
            reason = verify_response.invalid_reason or "Unknown reason"
            return self._create_402_response(
                payment_requirements, f"Invalid payment: {reason}"
            )

        # BEFORE calling handler - settle payment first (fail-fast)
        try:
            settle_response = await self.server.settle_payment(payment, selected_req)
        except Exception as e:
            logger.error(f"Exception during settlement for '{operation_id}': {e}")
            return self._create_402_response(
                payment_requirements, f"Payment settlement failed: {e}"
            )

        if not settle_response.success:
            reason = settle_response.error_reason or "Unknown"
            logger.error(f"Payment settlement failed for '{operation_id}': {reason}")
            return self._create_402_response(
                payment_requirements, f"Payment settlement failed: {reason}"
            )

        # Payment settled successfully - NOW call the handler
        response = await call_next(request)

        # Add payment response header with transaction info
        if 200 <= response.status_code < 300:
            response.headers[self.PAYMENT_RESPONSE_HEADER] = safe_base64_encode(
                settle_response.model_dump_json(by_alias=True)
            )
            tx_hash = getattr(settle_response, "transaction", None) or ""
            network = getattr(settle_response, "network", None) or ""
            if tx_hash:
                # selected_req.network is already CAIP-2 format like "eip155:8453"
                explorer_base = CUSTOM_NETWORKS.get(selected_req.network, {}).get("explorer_url", "")
                explorer_url = f"{explorer_base}{tx_hash}" if explorer_base else ""

                logger.info(
                    "Payment settled: tx=%s network=%s%s",
                    tx_hash,
                    network,
                    f" | {explorer_url}" if explorer_url else "",
                )

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
        """
        Constructs a 402 Payment Required response (v2 format).

        In v2, the payment requirements are sent in the PAYMENT-REQUIRED header
        (base64 encoded) as well as in the JSON body for backward compatibility.
        """
        payment_required = PaymentRequired(
            x402_version=2,
            error=error,
            accepts=requirements,
        )

        # JSON body for backward compatibility and human readability
        response_data = {
            "x402Version": 2,
            "accepts": [req.model_dump(by_alias=True) for req in requirements],
            "error": error,
        }

        response = JSONResponse(content=response_data, status_code=402)
        # Add the PAYMENT-REQUIRED header for v2 clients
        response.headers[PAYMENT_REQUIRED_HEADER] = encode_payment_required_header(
            payment_required
        )
        return response

    async def _get_operation_id(self, request: Request) -> str | None:
        """
        Determines the operation_id from the request, whether it's a REST or MCP call.
        """
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
        """
        Constructs a list of x402 v2 PaymentRequirements from our config.
        Uses CAIP-2 network identifiers and enhances with EIP-712 domain info.
        """
        accepts: list[PaymentRequirements] = []
        for option in options:
            network: Network | None = CHAIN_ID_TO_NETWORK.get(option.chain_id)
            if not network:
                logger.warning(
                    f"Unknown chain_id '{option.chain_id}' found in pricing config. "
                    "Skipping this payment option."
                )
                continue

            payee_address = self.settings.get_payee_address(network)
            if not payee_address:
                logger.warning(
                    f"No payee address configured for network '{network}'. "
                    "Skipping this payment option."
                )
                continue

            base_req = PaymentRequirements(
                scheme="exact",
                network=network,
                asset=option.token_address,
                amount=str(option.token_amount),
                pay_to=payee_address,
                max_timeout_seconds=60,
                extra={},  # Will be enhanced below
            )

            # Enhance with EIP-712 domain info if server is available
            if self.server:
                schemes = self.server._schemes.get(network, {})
                scheme = schemes.get("exact")
                if scheme:
                    # Get the supported kind for this network/scheme
                    supported = self.server._supported_responses.get(network, {}).get(
                        "exact"
                    )
                    if supported:
                        # Find matching kind
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
        """Find a requirement that matches the payment's accepted requirement."""
        # In v2, payment.accepted contains the requirement the client chose
        accepted = payment.accepted
        for req in requirements:
            if req.network == accepted.network and req.scheme == accepted.scheme:
                return req
        return None

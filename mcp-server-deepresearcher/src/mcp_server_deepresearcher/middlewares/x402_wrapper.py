"""
Payment-enforcing middleware that applies x402 pricing to REST and MCP calls.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging

import httpx
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.routing import Match
from x402.chains import NETWORK_TO_ID, get_token_name, get_token_version
from x402.common import find_matching_payment_requirements, x402_VERSION
from x402.encoding import safe_base64_decode
from x402.facilitator import FacilitatorClient
from x402.types import (
    PaymentPayload,
    PaymentRequirements,
    VerifyResponse,
    x402PaymentRequiredResponse,
)

from mcp_server_deepresearcher.x402_config import PaymentOption, X402Config, get_x402_settings

logger = logging.getLogger(__name__)

ID_TO_NETWORK_NAME = {int(v): k for k, v in NETWORK_TO_ID.items()}


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
    """

    FACILITATOR_VERIFY_MAX_RETRIES = 5
    FACILITATOR_VERIFY_RETRY_DELAY_SECONDS = 1.0

    def __init__(self, app, tool_pricing: dict[str, list[PaymentOption]]):
        super().__init__(app)
        self.tool_pricing = tool_pricing
        self.settings: X402Config = get_x402_settings()
        self.facilitator: FacilitatorClient | None = None
        if facilitator_config := self.settings.facilitator_config:
            if not self.settings.payee_wallet_address:
                logger.error(
                    "Facilitator is configured but payee_wallet_address is not set. "
                    "Payment middleware will be disabled."
                )
            else:
                self.facilitator = FacilitatorClient(facilitator_config)
        else:
            logger.warning(
                "No x402 facilitator configured (missing CDP keys and URL). "
                "Payment middleware will be disabled."
            )

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if not self.facilitator:
            return await call_next(request)

        # Cache request body for MCP POST requests to allow re-reading by downstream handlers
        if "mcp" in request.url.path and request.method == "POST":
            # Read and cache the body
            body_bytes = await request.body()
            # Wrap the receive callable to replay the cached body
            original_receive = request.scope["receive"]
            body_consumed = False
            
            async def cached_receive():
                nonlocal body_consumed
                if not body_consumed:
                    body_consumed = True
                    return {"type": "http.request", "body": body_bytes, "more_body": False}
                return await original_receive()
            
            request.scope["receive"] = cached_receive

        operation_id = await self._get_operation_id(request)
        pricing_options = self.tool_pricing.get(operation_id)

        if not operation_id or not pricing_options:
            return await call_next(request)

        payment_requirements = self._build_payment_requirements(
            pricing_options, request
        )
        if not (payment_header := request.headers.get("X-PAYMENT")):
            logger.warning(f"Payment header missing for '{operation_id}'")
            return self._create_402_response(
                payment_requirements, "No X-PAYMENT header provided"
            )

        try:
            payment_dict = json.loads(safe_base64_decode(payment_header))
            payment = PaymentPayload(**payment_dict)
        except Exception as e:
            client_host = request.client.host if request.client else "unknown"
            logger.warning(f"Invalid payment header from {client_host}: {e}")
            return self._create_402_response(
                payment_requirements, "Invalid payment header format"
            )

        selected_req = find_matching_payment_requirements(payment_requirements, payment)
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
                settle_response = await self.facilitator.settle(payment, selected_req)
                if settle_response.success:
                    response.headers["X-PAYMENT-RESPONSE"] = base64.b64encode(
                        settle_response.model_dump_json(by_alias=True).encode("utf-8")
                    ).decode("utf-8")
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
    ) -> VerifyResponse:
        last_error: httpx.HTTPError | None = None
        for attempt in range(1, max_retries + 1):
            try:
                return await self.facilitator.verify(payment, payment_requirements)
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
        if last_error is None:
            # This should never happen, but handle it gracefully
            raise RuntimeError("Payment verification failed but no error was captured")
        raise last_error

    def _create_402_response(
        self, requirements: list[PaymentRequirements], error: str
    ) -> JSONResponse:
        """Constructs a 402 Payment Required JSON response."""
        response_data = x402PaymentRequiredResponse(
            x402_version=x402_VERSION,
            accepts=requirements,
            error=error,
        ).model_dump(by_alias=True)
        return JSONResponse(content=response_data, status_code=402)

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
                # Body should already be cached in dispatch, read it
                body_bytes = await request.body()
                body = json.loads(body_bytes)
                return (body.get("params") or {}).get("name")
            except json.JSONDecodeError:
                logger.warning("Could not decode JSON body for MCP request.")
                return None
        return None

    def _build_payment_requirements(
        self, options: list[PaymentOption], request: Request
    ) -> list[PaymentRequirements]:
        """
        Constructs a list of x402.types.PaymentRequirements from our config.
        """
        accepts: list[PaymentRequirements] = []
        for option in options:
            network_name = ID_TO_NETWORK_NAME.get(option.chain_id)
            if not network_name:
                logger.warning(
                    f"Unknown chain_id '{option.chain_id}' found in pricing config. "
                    "This chain is not supported by the x402 library. "
                    "Skipping this payment option."
                )
                continue

            chain_id_str = str(option.chain_id)
            token_name = get_token_name(chain_id_str, option.token_address)
            token_version = get_token_version(chain_id_str, option.token_address)

            accepts.append(
                PaymentRequirements(
                    scheme="exact",
                    network=network_name,
                    asset=option.token_address,
                    max_amount_required=str(option.token_amount),
                    resource=str(request.url),
                    description=f"Payment for {request.url.path}",
                    mime_type=request.headers.get("content-type", ""),
                    pay_to=self.settings.payee_wallet_address,
                    max_timeout_seconds=60,
                    extra={
                        "name": token_name,
                        "version": token_version,
                    },
                )
            )
        return accepts


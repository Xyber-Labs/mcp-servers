from __future__ import annotations

import asyncio
import json
import os
from typing import Any

import httpx

from .config import E2ETestConfig

# Toggle between stateless and stateful MCP testing modes.
# Set MCP_TEST_STATELESS=false in .env.tests to test stateful servers.
MCP_STATELESS_MODE = os.getenv("MCP_TEST_STATELESS", "true").lower() == "true"


# =============================================================================
# Session Management
# =============================================================================


async def negotiate_mcp_session_id(
    config: E2ETestConfig,
    client: httpx.AsyncClient | None = None,
) -> str | None:
    """Perform StreamableHTTP handshake and return MCP session ID.

    Returns None in stateless mode (no session needed).
    If client is None, creates a temporary one.
    """
    if MCP_STATELESS_MODE:
        return None

    async def _negotiate(c: httpx.AsyncClient) -> str:
        headers = {"Accept": "text/event-stream"}
        async with c.stream("GET", "/mcp/", headers=headers) as response:
            session_id = response.headers.get("mcp-session-id")
            if not session_id:
                body = await response.aread()
                raise RuntimeError(
                    f"Streamable handshake failed: status={response.status_code}, "
                    f"body={body.decode('utf-8', 'ignore')}"
                )
            try:
                await asyncio.wait_for(response.aread(), timeout=0.1)
            except TimeoutError:
                pass
            finally:
                await response.aclose()
            return session_id

    if client is not None:
        return await _negotiate(client)

    async with httpx.AsyncClient(
        base_url=config.base_url, timeout=config.timeout_seconds
    ) as temp_client:
        return await _negotiate(temp_client)


async def initialize_mcp_session(
    config: E2ETestConfig,
    session_id: str | None,
    client: httpx.AsyncClient | None = None,
) -> None:
    """Send MCP initialize call for a given session ID.

    No-op in stateless mode.
    If client is None, creates a temporary one.
    """
    if MCP_STATELESS_MODE or session_id is None:
        return

    payload: dict[str, Any] = {
        "jsonrpc": "2.0",
        "id": 0,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-03-26",
            "capabilities": {"sampling": {}, "roots": {}},
            "clientInfo": {"name": "e2e_pytest_client", "version": "1.0.0"},
        },
    }
    headers = {
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
        "mcp-session-id": session_id,
    }

    async def _initialize(c: httpx.AsyncClient) -> None:
        response = await c.post("/mcp/", json=payload, headers=headers)
        response.raise_for_status()

    if client is not None:
        await _initialize(client)
    else:
        async with httpx.AsyncClient(
            base_url=config.base_url, timeout=config.timeout_seconds
        ) as temp_client:
            await _initialize(temp_client)


async def call_mcp_tool(
    config: E2ETestConfig,
    name: str,
    arguments: dict[str, Any],
    session_id: str | None = None,
    client: httpx.AsyncClient | None = None,
) -> httpx.Response:
    """Call an MCP tool via tools/call and return the raw HTTPX response.

    Works in both stateless and stateful modes.
    If client is None, creates a temporary one.
    """
    payload: dict[str, Any] = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": name, "arguments": arguments},
    }
    headers = {
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
    }
    if session_id and not MCP_STATELESS_MODE:
        headers["mcp-session-id"] = session_id

    if client is not None:
        return await client.post("/mcp/", json=payload, headers=headers)

    async with httpx.AsyncClient(
        base_url=config.base_url, timeout=config.timeout_seconds
    ) as temp_client:
        return await temp_client.post("/mcp/", json=payload, headers=headers)


# =============================================================================
# MCP Response Parsing
# =============================================================================


def parse_mcp_response(response: httpx.Response) -> tuple[bool, Any]:
    """
    Parse MCP response and return (is_error, data).

    Supports:
    - JSON responses
    - SSE responses (event stream)

    Returns:
        is_error: True if tool call failed
        data: structuredContent OR parsed content OR error payload
    """

    # --- HTTP-level error ---
    if response.status_code != 200:
        return True, {
            "http_status": response.status_code,
            "body": response.text,
        }

    raw_text = response.text.strip()

    # --- Parse body (JSON or SSE) ---
    try:
        if raw_text.startswith("event:") or raw_text.startswith("data:"):
            # SSE format
            data_lines = [
                line[5:].strip()
                for line in raw_text.splitlines()
                if line.startswith("data:")
            ]

            if not data_lines:
                return True, {"error": "SSE response missing data lines"}

            body = json.loads("".join(data_lines))
        else:
            body = response.json()
    except Exception as e:
        return True, {"error": f"Failed to parse response body: {e}"}

    # --- JSON-RPC protocol validation ---
    if not isinstance(body, dict):
        return True, {"error": "Response body is not a JSON object"}

    if body.get("error") is not None:
        return True, body["error"]

    result = body.get("result")
    if result is None:
        return True, {"error": "Missing 'result' field in response"}

    is_error = bool(result.get("isError", False))

    # --- Extract content ---
    if "structuredContent" in result:
        return is_error, result["structuredContent"]

    content = result.get("content")
    if content:
        text = content[0].get("text")
        if text is None:
            return True, {"error": "Missing text field in content"}

        try:
            return is_error, json.loads(text)
        except json.JSONDecodeError:
            # Not JSON — return raw text
            return is_error, text

    return is_error, None

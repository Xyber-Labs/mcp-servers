from __future__ import annotations

import asyncio
from typing import Any

import httpx

from .config import E2ETestConfig


async def negotiate_mcp_session_id(config: E2ETestConfig) -> str:
    """Perform StreamableHTTP handshake and return MCP session ID."""

    headers = {"Accept": "text/event-stream"}
    async with httpx.AsyncClient(
        base_url=config.base_url, timeout=config.timeout_seconds
    ) as client:
        async with client.stream("GET", "/mcp/", headers=headers) as response:
            session_id = response.headers.get("mcp-session-id")
            if not session_id:
                body = await response.aread()
                raise RuntimeError(
                    f"Streamable handshake failed: status={response.status_code}, body={body.decode('utf-8', 'ignore')}"
                )
            try:
                await asyncio.wait_for(response.aread(), timeout=0.1)
            except TimeoutError:
                pass
            finally:
                await response.aclose()
            return session_id


async def initialize_mcp_session(config: E2ETestConfig, session_id: str) -> None:
    """Send MCP initialize call for a given session ID."""

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
    async with httpx.AsyncClient(
        base_url=config.base_url, timeout=config.timeout_seconds
    ) as client:
        response = await client.post("/mcp/", json=payload, headers=headers)
        response.raise_for_status()


async def call_mcp_tool(
    config: E2ETestConfig,
    session_id: str,
    name: str,
    arguments: dict[str, Any],
) -> httpx.Response:
    """Call an MCP tool via tools/call and return the raw HTTPX response."""

    payload: dict[str, Any] = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": name, "arguments": arguments},
    }
    headers = {
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
        "mcp-session-id": session_id,
    }
    async with httpx.AsyncClient(
        base_url=config.base_url, timeout=config.timeout_seconds
    ) as client:
        return await client.post("/mcp/", json=payload, headers=headers)


# ============================================================================
# Variants that use a pre-configured x402 client (for paid tests)
# ============================================================================


async def negotiate_mcp_session_id_with_client(config: E2ETestConfig, client) -> str:
    """Perform StreamableHTTP handshake using provided client."""
    headers = {"Accept": "text/event-stream"}
    response = await client.get("/mcp/", headers=headers)
    session_id = response.headers.get("mcp-session-id")
    if not session_id:
        raise RuntimeError(
            f"Streamable handshake failed: status={response.status_code}, body={response.text}"
        )
    return session_id


async def initialize_mcp_session_with_client(
    config: E2ETestConfig, client, session_id: str
) -> None:
    """Send MCP initialize call using provided client."""
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
    response = await client.post("/mcp/", json=payload, headers=headers)
    response.raise_for_status()


async def call_mcp_tool_with_client(
    config: E2ETestConfig,
    client,
    session_id: str,
    name: str,
    arguments: dict[str, Any],
) -> httpx.Response:
    """Call an MCP tool using provided x402 client."""
    payload: dict[str, Any] = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": name, "arguments": arguments},
    }
    headers = {
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
        "mcp-session-id": session_id,
    }
    return await client.post("/mcp/", json=payload, headers=headers)


# ============================================================================
# MCP Response Parsing & Validation
# ============================================================================


def parse_mcp_response(response: httpx.Response) -> dict[str, Any]:
    """Parse and validate MCP JSON-RPC response structure.

    Ensures the MCP call succeeded and returns the result content.
    Raises AssertionError if the MCP response indicates an error.
    """
    import json

    assert response.status_code == 200, f"MCP request failed with status {response.status_code}"

    # Handle SSE format responses (event: message\r\ndata: {...})
    response_text = response.text
    if response_text.startswith("event:"):
        # Extract JSON from SSE format
        lines = response_text.split("\n")
        for line in lines:
            if line.startswith("data:"):
                json_str = line[5:].strip()  # Remove "data:" prefix
                body = json.loads(json_str)
                break
        else:
            raise AssertionError(f"No data line found in SSE response: {response_text[:200]}")
    else:
        # Regular JSON response
        body = response.json()

    assert "error" not in body or body.get("error") is None, f"MCP returned error: {body.get('error')}"
    assert "result" in body, "MCP response missing 'result' field"

    result = body["result"]

    # Check if structuredContent is available (preferred)
    if "structuredContent" in result:
        return result["structuredContent"]

    # Fallback to parsing text content
    assert "content" in result, "MCP result missing 'content' field"
    assert len(result["content"]) > 0, "MCP result content is empty"

    # Parse the tool output from the first content item
    content_text = result["content"][0].get("text", "")
    return json.loads(content_text)


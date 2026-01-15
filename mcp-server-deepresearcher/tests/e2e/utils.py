"""
Utilities for E2E tests.
"""

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


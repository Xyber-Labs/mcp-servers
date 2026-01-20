#!/usr/bin/env python3
"""
E2E tests for MCP tools for the Twitter Apify server.
Handles Server-Sent Events (SSE) format responses from FastMCP (Streamable HTTP).

These tests require a running server at http://localhost:8002.
Run with: uv run python -m pytest tests/test_mcp_tools.py

To run standalone: uv run python tests/test_mcp_tools.py
"""
import asyncio
import json
import os
from typing import Any

import httpx
import pytest
import pytest_asyncio

# These are true E2E tests that require a running server.
# They are skipped by default to keep `pytest` green in local/unit runs.
if os.getenv("RUN_MCP_E2E") != "1":
    pytest.skip(
        "Skipping MCP E2E tests (set RUN_MCP_E2E=1 and start the server to run).",
        allow_module_level=True,
    )


async def negotiate_mcp_session_id(base_url: str) -> str:
    """Perform StreamableHTTP handshake and return MCP session ID."""
    headers = {"Accept": "text/event-stream"}
    async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
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


async def initialize_mcp_session(base_url: str, session_id: str) -> None:
    """Send MCP initialize call for a given session ID."""
    payload: dict[str, Any] = {
        "jsonrpc": "2.0",
        "id": 0,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test-client", "version": "1.0.0"},
        },
    }
    headers = {
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
        "mcp-session-id": session_id,
    }
    async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
        response = await client.post("/mcp/", json=payload, headers=headers)
        response.raise_for_status()
        print(f"✓ Initialize successful: {response.status_code}")


async def call_mcp_tool(
    base_url: str,
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
    async with httpx.AsyncClient(base_url=base_url, timeout=60.0) as client:
        return await client.post("/mcp/", json=payload, headers=headers)


def parse_sse_response(text: str) -> dict[str, Any]:
    """Parse Server-Sent Events (SSE) format response."""
    # SSE format: "event: message\ndata: {...}"
    lines = text.strip().split("\n")
    data_lines = [line for line in lines if line.startswith("data: ")]
    if not data_lines:
        # Try to parse as plain JSON if not SSE format
        return json.loads(text)
    # Get the last data line (in case of multiple events)
    data_line = data_lines[-1]
    json_str = data_line.replace("data: ", "", 1)
    return json.loads(json_str)


def _assert_tool_ok(payload: dict[str, Any]) -> None:
    """Assert an MCP tool call response payload is not an error."""
    assert "result" in payload, f"Missing 'result' in payload: {payload}"
    result = payload["result"]
    # FastMCP often wraps tool output in MCP content blocks; errors are signaled via isError.
    if isinstance(result, dict) and result.get("isError"):
        error_text = ""
        try:
            error_text = result.get("content", [{}])[0].get("text", "")
        except Exception:
            error_text = str(result)
        raise AssertionError(f"MCP tool returned error: {error_text}")


async def list_mcp_tools(base_url: str, session_id: str) -> httpx.Response:
    """List all available MCP tools."""
    payload: dict[str, Any] = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/list",
    }
    headers = {
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
        "mcp-session-id": session_id,
    }
    async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
        return await client.post("/mcp/", json=payload, headers=headers)


# --- Pytest Fixtures ---

@pytest.fixture
def base_url() -> str:
    """Base URL for the MCP server."""
    return os.getenv("MCP_SERVER_URL", "http://localhost:8002")


@pytest_asyncio.fixture
async def mcp_session(base_url: str) -> str:
    """Fixture to negotiate and initialize an MCP session."""
    try:
        session_id = await negotiate_mcp_session_id(base_url)
        await initialize_mcp_session(base_url, session_id)
        return session_id
    except httpx.ConnectError:
        pytest.skip("MCP server not running - start server to run E2E tests")


# --- Pytest Tests ---

@pytest.mark.asyncio
@pytest.mark.integration
async def test_negotiate_mcp_session(base_url: str):
    """Test MCP session negotiation."""
    try:
        session_id = await negotiate_mcp_session_id(base_url)
        assert session_id is not None
        assert len(session_id) > 0
    except httpx.ConnectError:
        pytest.skip("MCP server not running - start server to run E2E tests")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_initialize_mcp_session(base_url: str):
    """Test MCP session initialization."""
    try:
        session_id = await negotiate_mcp_session_id(base_url)
        await initialize_mcp_session(base_url, session_id)
        # If no exception is raised, initialization succeeded
    except httpx.ConnectError:
        pytest.skip("MCP server not running - start server to run E2E tests")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_list_mcp_tools(base_url: str, mcp_session: str):
    """Test listing available MCP tools."""
    try:
        response = await list_mcp_tools(base_url, mcp_session)
        response.raise_for_status()
        
        tools_data = parse_sse_response(response.text)
        assert "result" in tools_data
        assert "tools" in tools_data["result"]
        
        tools = tools_data["result"]["tools"]
        assert isinstance(tools, list)
        assert len(tools) > 0
        
        # Verify tool structure
        for tool in tools:
            assert "name" in tool
            assert "description" in tool

        tool_names = {t.get("name") for t in tools}
        # Core tools exposed by this server
        expected = {
            "twitter_search_topic",
            "twitter_search_profile",
            "twitter_search_profile_latest",
            "twitter_search_replies",
            "twitter_search_profile_batch",
            "twitter_search_profile_latest_batch",
            "twitter_run_query",
            "twitter_list_types",
            "twitter_list_queries",
        }
        assert expected.issubset(tool_names), f"Missing tools: {expected - tool_names}"
    except httpx.ConnectError:
        pytest.skip("MCP server not running - start server to run E2E tests")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_mcp_list_types(base_url: str, mcp_session: str):
    """Test twitter_list_types tool."""
    try:
        response = await call_mcp_tool(base_url, mcp_session, name="twitter_list_types", arguments={})
        response.raise_for_status()
        payload = parse_sse_response(response.text)
        _assert_tool_ok(payload)
    except httpx.ConnectError:
        pytest.skip("MCP server not running - start server to run E2E tests")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_mcp_list_queries(base_url: str, mcp_session: str):
    """Test twitter_list_queries tool."""
    try:
        # Query type is optional; use topic to keep response bounded
        response = await call_mcp_tool(
            base_url,
            mcp_session,
            name="twitter_list_queries",
            arguments={"query_type": "topic"},
        )
        response.raise_for_status()
        payload = parse_sse_response(response.text)
        _assert_tool_ok(payload)
    except httpx.ConnectError:
        pytest.skip("MCP server not running - start server to run E2E tests")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_mcp_search_topic_tool(base_url: str, mcp_session: str):
    """Smoke test twitter_search_topic tool."""
    try:
        response = await call_mcp_tool(
            base_url,
            mcp_session,
            name="twitter_search_topic",
            arguments={
                "topic": "quantum computing",
                "max_items": 5,
                "sort": "Latest",
                "only_verified": False,
                "only_image": False,
                "lang": "en",
                "output_format": "min",
            },
        )
        response.raise_for_status()
        payload = parse_sse_response(response.text)
        _assert_tool_ok(payload)
    except httpx.ConnectError:
        pytest.skip("MCP server not running - start server to run E2E tests")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_mcp_search_profile_tool(base_url: str, mcp_session: str):
    """Smoke test twitter_search_profile tool."""
    try:
        response = await call_mcp_tool(
            base_url,
            mcp_session,
            name="twitter_search_profile",
            arguments={
                "username": "jack",
                "max_items": 5,
                "lang": "en",
                "output_format": "min",
            },
        )
        response.raise_for_status()
        payload = parse_sse_response(response.text)
        _assert_tool_ok(payload)
    except httpx.ConnectError:
        pytest.skip("MCP server not running - start server to run E2E tests")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_mcp_search_replies_tool(base_url: str, mcp_session: str):
    """Smoke test twitter_search_replies tool."""
    try:
        response = await call_mcp_tool(
            base_url,
            mcp_session,
            name="twitter_search_replies",
            arguments={
                "conversation_id": "1728108619189874825",
                "max_items": 5,
                "lang": "en",
                "output_format": "min",
            },
        )
        response.raise_for_status()
        payload = parse_sse_response(response.text)
        _assert_tool_ok(payload)
    except httpx.ConnectError:
        pytest.skip("MCP server not running - start server to run E2E tests")

# --- Standalone Execution (for manual testing) ---

async def main():
    """Main test function for standalone execution."""
    base_url = os.getenv("MCP_SERVER_URL", "http://localhost:8002")
    
    print("=" * 60)
    print("MCP Tools Testing (Standalone)")
    print("=" * 60)
    
    # Step 1: Negotiate session
    print("\n1. Negotiating MCP session...")
    try:
        session_id = await negotiate_mcp_session_id(base_url)
        print(f"✓ Session ID: {session_id}")
    except Exception as e:
        print(f"✗ Failed to negotiate session: {e}")
        return
    
    # Step 2: Initialize session
    print("\n2. Initializing MCP session...")
    try:
        await initialize_mcp_session(base_url, session_id)
    except Exception as e:
        print(f"✗ Failed to initialize session: {e}")
        return
    
    # Step 3: List tools
    print("\n3. Listing available tools...")
    try:
        response = await list_mcp_tools(base_url, session_id)
        response.raise_for_status()
        tools_data = parse_sse_response(response.text)
        print(f"✓ Tools list: {response.status_code}")
        if "result" in tools_data and "tools" in tools_data["result"]:
            tools = tools_data["result"]["tools"]
            print(f"  Found {len(tools)} tool(s):")
            for tool in tools:
                desc = tool.get("description", "no description")
                # Truncate long descriptions
                if len(desc) > 80:
                    desc = desc[:77] + "..."
                print(f"    - {tool.get('name', 'unknown')}: {desc}")
        else:
            print(f"  Response: {json.dumps(tools_data, indent=2)}")
    except Exception as e:
        print(f"✗ Failed to list tools: {e}")
        print(f"  Response: {response.text[:500] if 'response' in locals() else 'N/A'}")
    
    # Step 4: List types
    print("\n4. Testing twitter_list_types tool...")
    try:
        response = await call_mcp_tool(
            base_url,
            session_id,
            name="twitter_list_types",
            arguments={},
        )
        response.raise_for_status()
        result = parse_sse_response(response.text)
        print(f"✓ twitter_list_types: {response.status_code}")
        _assert_tool_ok(result)
    except Exception as e:
        print(f"✗ Failed to call twitter_list_types: {e}")
        print(f"  Response: {response.text[:500] if 'response' in locals() else 'N/A'}")
    
    # Step 5: Search topic
    print("\n5. Testing twitter_search_topic tool...")
    try:
        response = await call_mcp_tool(
            base_url,
            session_id,
            name="twitter_search_topic",
            arguments={
                "topic": "quantum computing",
                "max_items": 5,
                "sort": "Latest",
                "only_verified": False,
                "only_image": False,
                "lang": "en",
                "output_format": "min",
            },
        )
        result = parse_sse_response(response.text)
        print(f"  Status: {response.status_code}")
        if response.status_code == 200:
            _assert_tool_ok(result)
            print("✓ twitter_search_topic successful")
        else:
            print(f"  Response: {json.dumps(result, indent=2)[:500]}...")
    except Exception as e:
        print(f"✗ Failed to call twitter_search_topic: {e}")
        print(f"  Response: {response.text[:500] if 'response' in locals() else 'N/A'}")
    
    print("\n" + "=" * 60)
    print("Testing complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())


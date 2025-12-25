#!/usr/bin/env python3
"""
Test script for MCP tools using the same pattern as the template's e2e tests.
Handles Server-Sent Events (SSE) format responses from FastMCP.
"""
import asyncio
import json
from typing import Any

import httpx


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


async def main():
    """Main test function."""
    base_url = "http://localhost:8002"
    
    print("=" * 60)
    print("MCP Tools Testing")
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
    
    # Step 4: Test mcp_search_youtube_videos tool
    print("\n4. Testing mcp_search_youtube_videos tool...")
    try:
        response = await call_mcp_tool(
            base_url,
            session_id,
            name="mcp_search_youtube_videos",
            arguments={"query": "python tutorial", "max_results": 3},
        )
        response.raise_for_status()
        result = parse_sse_response(response.text)
        print(f"✓ Search tool: {response.status_code}")
        # Check for errors in result
        if "result" in result and isinstance(result["result"], dict):
            if result["result"].get("isError"):
                error_text = result["result"].get("content", [{}])[0].get("text", "Unknown error")
                print(f"  Error: {error_text}")
            else:
                print(f"  Success: {json.dumps(result, indent=2)[:500]}...")
        else:
            print(f"  Response: {json.dumps(result, indent=2)[:500]}...")
    except Exception as e:
        print(f"✗ Failed to call mcp_search_youtube_videos: {e}")
        print(f"  Response: {response.text[:500] if 'response' in locals() else 'N/A'}")
    
    # Step 5: Test extract_transcripts tool (requires APIFY_TOKEN)
    print("\n5. Testing extract_transcripts tool...")
    try:
        response = await call_mcp_tool(
            base_url,
            session_id,
            name="extract_transcripts",
            arguments={"video_ids": ["dQw4w9WgXcQ"]},
        )
        result = parse_sse_response(response.text)
        print(f"  Status: {response.status_code}")
        if response.status_code == 200:
            # Check for errors in result
            if "result" in result and isinstance(result["result"], dict):
                if result["result"].get("isError"):
                    error_text = result["result"].get("content", [{}])[0].get("text", "Unknown error")
                    print(f"  Error: {error_text[:200]}...")
                else:
                    print(f"✓ Extract transcripts successful")
                    print(f"  Response: {json.dumps(result, indent=2)[:500]}...")
            else:
                print(f"✓ Extract transcripts successful")
                print(f"  Response: {json.dumps(result, indent=2)[:500]}...")
        else:
            print(f"  Response: {json.dumps(result, indent=2)}")
    except Exception as e:
        print(f"✗ Failed to call extract_transcripts: {e}")
        print(f"  Response: {response.text[:500] if 'response' in locals() else 'N/A'}")
    
    print("\n" + "=" * 60)
    print("Testing complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())


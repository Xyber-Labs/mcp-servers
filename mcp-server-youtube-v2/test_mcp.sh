#!/bin/bash
# Test script for MCP tools using curl
# Based on the template's e2e test utilities

BASE_URL="http://localhost:8002"
MCP_ENDPOINT="${BASE_URL}/mcp/"

echo "============================================================"
echo "MCP Tools Testing (curl-based)"
echo "============================================================"

# Step 1: Negotiate Session ID
echo ""
echo "1. Negotiating MCP session..."
SESSION_RESPONSE=$(curl -s -X GET "${MCP_ENDPOINT}" \
  -H "Accept: text/event-stream" \
  -i)

SESSION_ID=$(echo "$SESSION_RESPONSE" | grep -i "mcp-session-id" | cut -d' ' -f2 | tr -d '\r\n')

if [ -z "$SESSION_ID" ]; then
    echo "✗ Failed to get session ID"
    echo "Response:"
    echo "$SESSION_RESPONSE"
    exit 1
fi

echo "✓ Session ID: $SESSION_ID"

# Step 2: Initialize MCP Session
echo ""
echo "2. Initializing MCP session..."
INIT_RESPONSE=$(curl -s -X POST "${MCP_ENDPOINT}" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "mcp-session-id: ${SESSION_ID}" \
  -d '{
    "jsonrpc": "2.0",
    "id": 0,
    "method": "initialize",
    "params": {
      "protocolVersion": "2024-11-05",
      "capabilities": {},
      "clientInfo": {
        "name": "test-client",
        "version": "1.0.0"
      }
    }
  }')

if echo "$INIT_RESPONSE" | grep -q '"error"'; then
    echo "✗ Initialize failed"
    echo "$INIT_RESPONSE" | jq '.' 2>/dev/null || echo "$INIT_RESPONSE"
    exit 1
else
    echo "✓ Initialize successful"
fi

# Step 3: List Tools
echo ""
echo "3. Listing available tools..."
TOOLS_RESPONSE=$(curl -s -X POST "${MCP_ENDPOINT}" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "mcp-session-id: ${SESSION_ID}" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list"
  }')

echo "Tools list response:"
# Parse SSE format if present
if echo "$TOOLS_RESPONSE" | grep -q "^data:"; then
    echo "$TOOLS_RESPONSE" | grep "^data:" | sed 's/^data: //' | jq '.' 2>/dev/null || echo "$TOOLS_RESPONSE"
else
    echo "$TOOLS_RESPONSE" | jq '.' 2>/dev/null || echo "$TOOLS_RESPONSE"
fi

# Step 4: Test mcp_search_youtube_videos tool
echo ""
echo "4. Testing mcp_search_youtube_videos tool..."
SEARCH_RESPONSE=$(curl -s -X POST "${MCP_ENDPOINT}" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "mcp-session-id: ${SESSION_ID}" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/call",
    "params": {
      "name": "mcp_search_youtube_videos",
      "arguments": {
        "query": "python tutorial",
        "max_results": 3
      }
    }
  }')

echo "Search tool response:"
# Parse SSE format if present
if echo "$SEARCH_RESPONSE" | grep -q "^data:"; then
    echo "$SEARCH_RESPONSE" | grep "^data:" | sed 's/^data: //' | jq '.' 2>/dev/null || echo "$SEARCH_RESPONSE"
else
    echo "$SEARCH_RESPONSE" | jq '.' 2>/dev/null || echo "$SEARCH_RESPONSE"
fi

# Step 5: Test extract_transcripts tool (requires APIFY_TOKEN)
echo ""
echo "5. Testing extract_transcripts tool..."
EXTRACT_RESPONSE=$(curl -s -X POST "${MCP_ENDPOINT}" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "mcp-session-id: ${SESSION_ID}" \
  -d '{
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": {
      "name": "extract_transcripts",
      "arguments": {
        "video_ids": ["dQw4w9WgXcQ"]
      }
    }
  }')

echo "Extract transcripts response:"
# Parse SSE format if present
if echo "$EXTRACT_RESPONSE" | grep -q "^data:"; then
    echo "$EXTRACT_RESPONSE" | grep "^data:" | sed 's/^data: //' | jq '.' 2>/dev/null || echo "$EXTRACT_RESPONSE"
else
    echo "$EXTRACT_RESPONSE" | jq '.' 2>/dev/null || echo "$EXTRACT_RESPONSE"
fi

echo ""
echo "============================================================"
echo "Testing complete!"
echo "============================================================"


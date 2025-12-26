#!/bin/bash
# Script to start the server and run E2E tests

set -e

echo "=========================================="
echo "Starting MCP YouTube Server..."
echo "=========================================="

# Start server in background
uv run python -m mcp_server_youtube --port 8002 &
SERVER_PID=$!

# Wait for server to be ready
echo "Waiting for server to start..."
sleep 3

# Check if server is running
if ! curl -s http://localhost:8002/api/health > /dev/null; then
    echo "Error: Server failed to start"
    kill $SERVER_PID 2>/dev/null || true
    exit 1
fi

echo "✓ Server is running (PID: $SERVER_PID)"
echo ""

# Run E2E tests
echo "=========================================="
echo "Running E2E Tests..."
echo "=========================================="
uv run python -m pytest tests/test_mcp_tools.py -v

# Capture exit code
TEST_EXIT_CODE=$?

# Cleanup: Stop the server
echo ""
echo "=========================================="
echo "Stopping server..."
echo "=========================================="
kill $SERVER_PID 2>/dev/null || true
wait $SERVER_PID 2>/dev/null || true

exit $TEST_EXIT_CODE


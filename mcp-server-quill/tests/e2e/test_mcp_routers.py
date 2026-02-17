"""
E2E smoke tests for MCP-only endpoints.

Test coverage:
- Currently no MCP-only tools/endpoints exist in mcp-server-quill
- All MCP tools are hybrid endpoints (accessible via both REST and MCP)
- Tests for those tools are in test_hybrid_routers.py

This file serves as a placeholder for future MCP-only tools.
"""

from __future__ import annotations

# No tests currently - mcp_routers is empty
# When MCP-only tools are added, add tests here following the pattern:
# - test_mcp_tool_name_mcp_pricing_off() for free/pricing-off scenarios
# - test_mcp_tool_name_mcp_no_payment() for pricing-on without payment
# - test_mcp_tool_name_mcp_with_payment() for pricing-on with payment

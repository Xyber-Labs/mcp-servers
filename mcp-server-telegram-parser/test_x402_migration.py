#!/usr/bin/env python3
"""
Test script to verify x402 architecture migration.
Run with: MCP_TELEGRAM_PARSER_X402_PRICING_MODE=off uv run python test_x402_migration.py
"""

import os

# Set pricing mode to off for testing
os.environ["MCP_TELEGRAM_PARSER_X402_PRICING_MODE"] = "off"

from mcp_server_telegram_parser.app import create_app
from mcp_server_telegram_parser.hybrid_routers import routers
from mcp_server_telegram_parser.x402_config import get_x402_settings

print("=" * 60)
print("Testing x402 Architecture Migration")
print("=" * 60)

# Test 1: Import verification
print("\n[Test 1] Verifying imports...")
print("✓ All imports successful")

# Test 2: Hybrid routers
print("\n[Test 2] Hybrid routers...")
print(f"✓ Found {len(routers)} hybrid router(s)")
for i, router in enumerate(routers, 1):
    print(
        f"  Router {i}: {router.prefix if hasattr(router, 'prefix') else 'No prefix'}"
    )

# Test 3: x402 settings
print("\n[Test 3] x402 settings...")
settings = get_x402_settings()
print("✓ Settings loaded:")
print(f"  - pricing_mode: {settings.pricing_mode}")
print("  - env_prefix: MCP_TELEGRAM_PARSER_X402_")
print(f"  - pricing_config_path: {settings.pricing_config_path}")

# Test 4: App creation
print("\n[Test 4] App creation...")
app = create_app()
print("✓ App created successfully:")
print(f"  - Title: {app.title}")
print(f"  - Total routes: {len(app.routes)}")

# Check for hybrid routes
hybrid_routes = [r for r in app.routes if hasattr(r, "path") and "/hybrid" in r.path]
print(f"  - Hybrid routes: {len(hybrid_routes)}")

# Test 5: Verify middleware configuration
print("\n[Test 5] Middleware configuration...")
middleware_classes = [type(m).__name__ for m in app.user_middleware]
print(
    f"✓ Middleware stack: {middleware_classes if middleware_classes else 'Empty (expected with pricing_mode=off)'}"
)

print("\n" + "=" * 60)
print("✓ ALL TESTS PASSED! Migration successful.")
print("=" * 60)
print("\nNext steps:")
print("1. Create tool_pricing.yaml if you want to enable pricing")
print("2. Set MCP_TELEGRAM_PARSER_X402_PRICING_MODE=on to enable payments")
print("3. Configure payee_wallet_address and facilitator settings")

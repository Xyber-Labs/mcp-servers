import asyncio
import logging
import sys

from langchain_mcp_adapters.client import MultiServerMCPClient
from mcp_server_deepresearcher.deepresearcher.utils import load_mcp_servers_config
from mcp_server_deepresearcher.deepresearcher.config import Settings

logger = logging.getLogger(__name__)



async def initialize_mcp_servers():
    """
    Initialize MCP servers and return tools with their source server information.
    
    Returns:
        tuple: (mcp_tools, tool_to_server_map) where:
            - mcp_tools: List of tool objects
            - tool_to_server_map: Dict mapping tool names to MCP server names
    """
    settings = Settings()
    MCP_SERVERS_CONFIG = load_mcp_servers_config(
        mcp_tavily_url=settings.search_mcp.MCP_TAVILY_URL,
        mcp_arxiv_url=settings.search_mcp.MCP_ARXIV_URL,
        mcp_twitter_url=settings.search_mcp.MCP_TWITTER_APIFY_URL,
        mcp_youtube_url=settings.search_mcp.MCP_YOUTUBE_APIFY_URL,
        mcp_telegram_parser_url=settings.search_mcp.MCP_TELEGRAM_PARSER_URL,
        mcp_deepresearch_url=settings.search_mcp.MCP_DEEPRESEARCH_URL
    )

    # Try to connect to each MCP server individually
    mcp_tools = []
    tool_to_server_map = {}  # Map tool names to their MCP server names
    successful_servers = []
    failed_servers = []

    logger.info("=" * 80)
    logger.info("MCP SERVER CONNECTION ATTEMPTS")
    logger.info("=" * 80)
    logger.info(f"Total servers to connect: {len(MCP_SERVERS_CONFIG)}")
    logger.info("=" * 80)

    for server_name, server_config in MCP_SERVERS_CONFIG.items():
        try:
            url = server_config.get('url', 'No URL')
            logger.info(f"[{server_name.upper()}] Connecting to {url}...")

            # Create a single-server client for this server
            single_server_config = {server_name: server_config}
            single_client = MultiServerMCPClient(single_server_config)

            # Try to get tools from this specific server with timeout
            server_tools = await asyncio.wait_for(
                single_client.get_tools(), timeout=30.0
            )

            if server_tools:
                # Track which server each tool belongs to
                for tool in server_tools:
                    tool_name = getattr(tool, "name", None) or str(tool)
                    tool_to_server_map[tool_name] = server_name
                mcp_tools.extend(server_tools)
                successful_servers.append(server_name.upper())
                logger.info(f"[{server_name.upper()}] ✓ Connected ({len(server_tools)} tools)")
            else:
                successful_servers.append(server_name.upper())
                logger.warning(f"[{server_name.upper()}] ⚠ Connected but no tools returned")

        except asyncio.TimeoutError:
            failed_servers.append(server_name.upper())
            logger.error(f"[{server_name.upper()}] ✗ Timeout (30s)")
            continue
        except Exception as e:
            failed_servers.append(server_name.upper())
            error_message = str(e)
            # Check for ExceptionGroup and extract sub-exceptions for clearer logging
            if hasattr(e, "exceptions") and e.exceptions:
                sub_exc = e.exceptions[0]
                error_message = f"{type(sub_exc).__name__}: {sub_exc}"

            # Extract HTTP status for concise error message
            if "500" in error_message:
                logger.error(f"[{server_name.upper()}] ✗ Server error (500)")
            elif "401" in error_message or "Unauthorized" in error_message:
                logger.error(f"[{server_name.upper()}] ✗ Authentication failed")
            elif "404" in error_message or "Not Found" in error_message:
                logger.error(f"[{server_name.upper()}] ✗ Not found (404)")
            else:
                logger.error(f"[{server_name.upper()}] ✗ Connection failed")
            continue

    # Log summary with successful MCPs listed
    logger.info("")
    logger.info("=" * 80)
    logger.info("MCP CONNECTION SUMMARY")
    logger.info("=" * 80)
    if successful_servers:
        logger.info(f"✓ Successful MCPs ({len(successful_servers)}): {', '.join(successful_servers)}")
    if failed_servers:
        logger.info(f"✗ Failed MCPs ({len(failed_servers)}): {', '.join(failed_servers)}")
    logger.info(f"Total tools available: {len(mcp_tools)}")
    logger.info("=" * 80)

    if len(successful_servers) == 0:
        logger.error("")
        logger.error("=" * 80)
        logger.error("CRITICAL ERROR: No MCP servers could be initialized!")
        logger.error("=" * 80)
        logger.error("All connection attempts failed. Please check:")
        logger.error("  1. Server URLs are correct")
        logger.error("  2. API tokens are valid (if required)")
        logger.error("  3. Network connectivity")
        logger.error("  4. Servers are running and accessible")
        logger.error("=" * 80)
        sys.exit(1)
    else:
        logger.info("")

    return mcp_tools, tool_to_server_map


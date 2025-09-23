import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError
from loguru import logger

from mcp_server_together_imgen.schemas import ImageGenerationRequest
from mcp_server_together_imgen.together_ai.together_client import (
    TogetherClient,
    get_together_client,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[dict[str, Any]]:
    """Manage server startup/shutdown. Initializes required services."""
    logger.info("Lifespan: Initializing services...")
    try:
        together_client = get_together_client()
        logger.info("Lifespan: Services initialized successfully")
        yield {"together_client": together_client}
    except Exception as startup_err:
        logger.error(
            f"FATAL: Unexpected error during lifespan initialization: {startup_err}",
            exc_info=True,
        )
        raise startup_err
    finally:
        logger.info("Lifespan: Shutdown cleanup completed")


mcp_server = FastMCP("together-imgen-server", lifespan=app_lifespan)


@mcp_server.tool()
async def generate_image(
    ctx: Context,
    request: ImageGenerationRequest,
) -> str:
    """Generates an image based on a text prompt."""
    together_client: TogetherClient = ctx.request_context.lifespan_context[
        "together_client"
    ]
    logger.info(f"Generating image for prompt: {request.prompt}")

    try:
        if request.refine_prompt:
            logger.info("Refining prompt...")
            request.prompt = await together_client.refine_prompt(request.prompt)
            logger.info(f"Refined prompt: {request.prompt}")

        b64_image = await together_client.generate_image_b64(request)
        return b64_image
    except Exception as e:
        logger.error(f"Failed to generate image: {e}", exc_info=True)
        raise ToolError(f"Failed to generate image: {e}") from e

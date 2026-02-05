import base64
import logging

from fastapi import APIRouter, Request
from fastmcp.exceptions import ToolError

from mcp_server_stability.schemas import ImageGenerationRequest
from mcp_server_stability.stable_diffusion import (
    StabilityService,
    StableDiffusionClientError,
    StableDiffusionServerConnectionError,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/generate-image",
    tags=["Stability"],
    operation_id="stability_generate_image",
)
async def generate_image(
    request_body: ImageGenerationRequest,
    request: Request,
) -> str:
    """Generate an image from a prompt using Stable Diffusion and returns it as a base64 encoded string"""
    stability_service: StabilityService = request.app.state.stability_service

    try:
        # Use validated data for parameters
        params = {
            "prompt": request_body.prompt,
            "negative_prompt": request_body.negative_prompt,
            "aspect_ratio": request_body.aspect_ratio,
            "seed": request_body.seed,
        }
        if request_body.style_preset:
            params["style_preset"] = request_body.style_preset

        response = await stability_service.send_generation_request(params)
        finish_reason = response.headers.get("finish-reason")
        if finish_reason == "CONTENT_FILTERED":
            raise ToolError("Generation failed: NSFW content filtered")

        # Convert the image to a base64 encoded string
        image_data = response.content
        base64_image = base64.b64encode(image_data).decode("utf-8")
        return base64_image

    except (StableDiffusionServerConnectionError, StableDiffusionClientError) as exc:
        logger.error(f"Stable Diffusion error: {exc}")
        raise ToolError(str(exc)) from exc
    except Exception as exc:
        logger.error(f"Unexpected error: {exc}", exc_info=True)
        raise ToolError(f"Unexpected error: {exc}") from exc

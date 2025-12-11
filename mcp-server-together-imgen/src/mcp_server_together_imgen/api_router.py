from fastapi import APIRouter, Depends, HTTPException, Response
from loguru import logger
from together.error import InvalidRequestError

from mcp_server_together_imgen.schemas import (
    ImageGenerationRequest,
)
from mcp_server_together_imgen.together_ai.together_client import (
    TogetherClient,
    get_together_client,
)

router = APIRouter()


@router.post(
    "/images",
    tags=["api"],
    operation_id="generate_image",
)
async def generate_image(
    request: ImageGenerationRequest,
    together_client: TogetherClient = Depends(get_together_client),
):
    """Generates an image from a text prompt and returns it as a base64 string."""
    try:
        logger.info(f"Received image generation request for prompt: {request.prompt}")
        if request.refine_prompt:
            logger.info("Refining prompt...")
            request.prompt = await together_client.refine_prompt(request.prompt)
            logger.info(f"Refined prompt: {request.prompt}")

        logger.info("Starting image generation...")
        image_b64 = await together_client.generate_image_b64(request)
        logger.info("Image generation completed successfully")
        return Response(content=image_b64)
    except InvalidRequestError as e:
        logger.error(f"Upstream API request error: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Upstream API request error: {e}",
        )
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")

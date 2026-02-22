import logging

from fastapi import APIRouter, Depends, HTTPException

from mcp_server_together_imgen.dependencies import get_together_client
from mcp_server_together_imgen.schemas import ImageResponse
from mcp_server_together_imgen.together.client import TogetherClient

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/generate",
    tags=["Image Generation"],
    operation_id="generate_image",
    response_model=ImageResponse,
)
async def generate_image(
    prompt: str,
    refine_prompt: bool = False,
    width: int = 1024,
    height: int = 1024,
    steps: int | None = None,
    guidance_scale: float | None = None,
    negative_prompt: str | None = None,
    seed: int | None = None,
    together_client: TogetherClient = Depends(get_together_client),
) -> ImageResponse:
    """
    Generate an image from a text prompt.

    This endpoint generates images using the Together AI API with the model
    configured via environment variable (default: FLUX.1-dev).

    Args:
        prompt: The text description of the image to generate
        refine_prompt: Whether to refine the prompt using a chat model before generation
        width: Image width in pixels (must be multiple of 8)
        height: Image height in pixels (must be multiple of 8)
        steps: Number of generation steps (if supported by model)
        guidance_scale: Guidance scale (if supported by model)
        negative_prompt: Negative prompt (if supported by model)
        seed: Random seed for reproducibility (use None for random)

    Returns:
        ImageResponse with base64-encoded image and metadata
    """
    try:
        logger.info(f"Generating image with prompt: {prompt[:100]}...")

        # Refine prompt if requested
        refined_prompt_text = None
        actual_prompt = prompt
        if refine_prompt:
            logger.info("Refining prompt...")
            actual_prompt = await together_client.refine_prompt(prompt, mode="standard")
            refined_prompt_text = actual_prompt
            logger.info(f"Refined prompt: {actual_prompt[:100]}...")

        # Generate image using model from settings
        logger.info("Starting image generation...")
        image_b64 = await together_client.generate_image(
            prompt=actual_prompt,
            model=None,  # Use default from settings
            width=width,
            height=height,
            steps=steps,
            guidance_scale=guidance_scale,
            negative_prompt=negative_prompt,
            seed=seed,
        )
        logger.info("Image generation completed successfully")

        return ImageResponse(
            image_base64=image_b64,
            model_used=together_client.settings.default_model,
            refined_prompt=refined_prompt_text,
        )

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating image: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Image generation failed: {str(e)}")


@router.post(
    "/generate-lora",
    tags=["Image Generation"],
    operation_id="generate_image_with_lora",
    response_model=ImageResponse,
)
async def generate_image_with_lora(
    prompt: str,
    lora_url: str | None = None,
    lora_scale: float = 0.9,
    refine_prompt: bool = False,
    width: int = 1024,
    height: int = 1024,
    steps: int | None = None,
    guidance_scale: float | None = None,
    seed: int | None = None,
    together_client: TogetherClient = Depends(get_together_client),
) -> ImageResponse:
    """
    Generate an image from a text prompt using a LoRA model.

    This endpoint generates images using LoRA (Low-Rank Adaptation) models, which allow
    for fine-tuned style or content modifications. Uses the model configured via
    environment variable (default: FLUX.1-dev-lora).

    Args:
        prompt: The text description of the image to generate
        lora_url: URL to the LoRA model weights (optional, defaults to env config)
        lora_scale: Scale factor for LoRA influence (0.0-1.0, default 1.0)
        refine_prompt: Whether to refine the prompt using a chat model before generation
        width: Image width in pixels (must be multiple of 8)
        height: Image height in pixels (must be multiple of 8)
        steps: Number of generation steps (if supported by model)
        guidance_scale: Guidance scale (if supported by model)
        seed: Random seed for reproducibility (use None for random)

    Returns:
        ImageResponse with base64-encoded image and metadata including LoRA URL
    """
    try:
        # Use default LoRA URL from settings if not provided
        actual_lora_url = lora_url or together_client.settings.lora_url
        if not actual_lora_url:
            raise ValueError(
                "lora_url is required - either provide it in the request or configure LORA_URL env var"
            )
        if not (0.0 <= lora_scale <= 2.0):
            raise ValueError("lora_scale must be between 0.0 and 2.0")

        logger.info(f"Generating image with LoRA: {actual_lora_url[:100]}...")
        logger.info(f"Prompt: {prompt[:100]}...")

        # Refine prompt if requested
        refined_prompt_text = None
        actual_prompt = prompt
        if refine_prompt:
            logger.info("Refining prompt...")
            actual_prompt = await together_client.refine_prompt(prompt, mode="lora")
            refined_prompt_text = actual_prompt
            logger.info(f"Refined prompt: {actual_prompt[:100]}...")

        # Generate image using model from settings
        logger.info("Starting LoRA image generation...")
        image_b64 = await together_client.generate_image_with_lora(
            prompt=actual_prompt,
            lora_url=actual_lora_url,
            lora_scale=lora_scale,
            model=None,  # Use default from settings
            width=width,
            height=height,
            steps=steps,
            guidance_scale=guidance_scale,
            seed=seed,
        )
        logger.info("LoRA image generation completed successfully")

        return ImageResponse(
            image_base64=image_b64,
            model_used=together_client.settings.lora_model,
            refined_prompt=refined_prompt_text,
            lora_url=actual_lora_url,
        )

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating LoRA image: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"LoRA image generation failed: {str(e)}"
        )

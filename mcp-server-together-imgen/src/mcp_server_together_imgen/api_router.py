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
from mcp_server_together_imgen.together_ai.model_registry import (
    list_available_models,
    get_model_schema,
)

router = APIRouter()


@router.get(
    "/models",
    tags=["api"],
    operation_id="list_models",
)
async def list_models():
    """List all available image generation models and their capabilities."""
    models_info = []
    for model_name in list_available_models():
        schema = get_model_schema(model_name)
        models_info.append({
            "model": schema.model_name,
            "family": schema.family.value,
            "capabilities": {
                "supports_negative_prompt": schema.capabilities.supports_negative_prompt,
                "supports_guidance_scale": schema.capabilities.supports_guidance_scale,
                "supports_guidance_param": schema.capabilities.supports_guidance_param,
                "supports_steps": schema.capabilities.supports_steps,
                "supports_lora": schema.capabilities.supports_lora,
                "requires_disable_safety_checker": schema.capabilities.requires_disable_safety_checker,
                "response_format": schema.capabilities.response_format,
                "default_response_format": schema.capabilities.default_response_format,
            }
        })
    return {"models": models_info}


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
        # Validate request - check if prompt and model fields might be swapped
        available_models = list_available_models()
        prompt_looks_like_model = (
            request.prompt.startswith("black-forest-labs/") 
            or request.prompt.startswith("flux")
            or any(model in request.prompt.lower() for model in ["flux.1", "flux.2", "flux-1", "flux-2"])
        )
        model_looks_like_prompt = (
            request.model 
            and not request.model.startswith("black-forest-labs/")
            and request.model not in available_models
            and len(request.model.split()) > 2  # Prompts are usually longer
        )
        
        if prompt_looks_like_model and model_looks_like_prompt:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"It looks like you may have swapped the 'prompt' and 'model' fields. "
                    f"Your prompt is '{request.prompt}' (looks like a model name) and "
                    f"your model is '{request.model}' (looks like a prompt). "
                    f"Please swap them: use 'prompt' for your image description and 'model' for the model name. "
                    f"Available models: {', '.join(available_models)}"
                )
            )
        
        logger.info(f"Received image generation request for prompt: {request.prompt}")
        
        # Validate model and automatically filter unsupported parameters
        if request.model:
            logger.info(f"Using specified model: {request.model}")
            try:
                model_schema = get_model_schema(request.model)
                
                # Log warnings for unsupported parameters (but don't fail - they'll be filtered automatically)
                if request.steps is not None and not model_schema.capabilities.supports_steps:
                    logger.warning(f"Parameter 'steps' is not supported for {request.model}. It will be automatically removed.")
                if request.guidance_scale is not None and not model_schema.capabilities.supports_guidance_scale and not model_schema.capabilities.supports_guidance_param:
                    logger.warning(f"Parameter 'guidance_scale' is not supported for {request.model}. It will be automatically removed.")
                if request.negative_prompt is not None and not model_schema.capabilities.supports_negative_prompt:
                    logger.warning(f"Parameter 'negative_prompt' is not supported for {request.model}. It will be automatically removed.")
                if request.lora_scale and request.lora_scale > 0 and not model_schema.capabilities.supports_lora:
                    logger.warning(f"Parameter 'lora_scale' is not supported for {request.model}. It will be automatically removed.")
            except ValueError as e:
                # Model not found - this is still an error
                available_models = list_available_models()
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid model '{request.model}'. {str(e)} Available models: {', '.join(available_models)}"
                )
        
        if request.refine_prompt:
            logger.info("Refining prompt...")
            request.prompt = await together_client.refine_prompt(request.prompt)
            logger.info(f"Refined prompt: {request.prompt}")

        logger.info("Starting image generation...")
        image_b64 = await together_client.generate_image_b64(request)
        logger.info("Image generation completed successfully")
        return Response(content=image_b64)
    except HTTPException:
        # Re-raise HTTP exceptions (like our validation errors)
        raise
    except ValueError as e:
        error_msg = str(e)
        if "not found in registry" in error_msg:
            available_models = list_available_models()
            logger.error(f"Invalid model specified: {e}")
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Invalid model. {error_msg}. "
                    f"Available models: {', '.join(available_models)}"
                )
            )
        raise HTTPException(status_code=400, detail=str(e))
    except InvalidRequestError as e:
        error_msg = str(e)
        logger.error(f"Upstream API request error: {e}")
        
        # Parse Together API error messages for better user feedback
        if "not supported" in error_msg.lower() or "remove this parameter" in error_msg.lower():
            # Extract parameter name from error if possible
            import re
            param_match = re.search(r"Parameter '(\w+)'", error_msg)
            if param_match:
                param_name = param_match.group(1)
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Parameter '{param_name}' is not supported for the selected model '{request.model if request.model else 'default'}'. "
                        f"Please remove '{param_name}' from your request or use a different model. "
                        f"Check /api/models endpoint for model capabilities."
                    )
                )
        
        raise HTTPException(
            status_code=400,
            detail=f"Together API error: {error_msg}",
        )
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")

import asyncio
from functools import lru_cache
import json

import httpx
from loguru import logger
from together import AsyncTogether

from mcp_server_together_imgen.together_ai.config import TogetherSettings
from mcp_server_together_imgen.schemas import ImageGenerationRequest
from mcp_server_together_imgen.together_ai.model_registry import get_model_schema


class TogetherClient:
    def __init__(self, settings: TogetherSettings):
        self.settings = settings
        # Configure client with explicit timeout settings
        # FLUX.2 can take 60-180+ seconds, so we need a longer timeout
        # The timeout parameter is in seconds for httpx (used internally)
        self.client = AsyncTogether(
            api_key=self.settings.api_key,
            timeout=300.0  # 5 minutes timeout for FLUX.2 image generation
        )

    async def refine_prompt(self, user_prompt: str) -> str:
        """Rewrites the prompt using the Together Chat API."""
        try:
            response = await self.client.chat.completions.create(
                model=self.settings.refiner_model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful prompt rewriter for image models.",
                    },
                    {
                        "role": "user",
                        "content": (self.settings.instruction_text or "") + user_prompt,
                    },
                ],
                temperature=0.2,
            )
            refined = (response.choices[0].message.content or "").strip()
            return refined or user_prompt
        except Exception as e:
            logger.error(f"Failed to refine prompt, falling back: {e}")
            return user_prompt

    async def generate_image_b64(self, request: ImageGenerationRequest) -> str:
        """Generates a base64 PNG image using the Together Images API."""
        # Determine which model to use
        if request.model:
            # Use explicitly specified model
            model = request.model
            model_schema = get_model_schema(model)
        elif request.lora_scale is not None and request.lora_scale > 0:
            # Use LoRA model if LoRA is requested
            model = self.settings.lora_image_model
            model_schema = get_model_schema(model)
        else:
            # Use default non-LoRA model
            model = self.settings.non_lora_image_model
            model_schema = get_model_schema(model)

        logger.info(f"Using model: {model} (family: {model_schema.family.value})")

        # Prepare request parameters for model schema
        # Only include parameters that are not None and are supported by the model
        request_params = {
            "prompt": request.prompt,
        }
        
        # Add optional parameters only if they are provided
        if request.width is not None:
            request_params["width"] = request.width
        if request.height is not None:
            request_params["height"] = request.height
        # Only include steps if model supports it AND it's provided
        if model_schema.capabilities.supports_steps and request.steps is not None:
            request_params["steps"] = request.steps
        if request.seed is not None and request.seed != 0:
            request_params["seed"] = request.seed
        # Only include guidance_scale if model supports it AND it's provided
        if (model_schema.capabilities.supports_guidance_scale or model_schema.capabilities.supports_guidance_param) and request.guidance_scale is not None:
            request_params["guidance_scale"] = request.guidance_scale
        # Only include negative_prompt if model supports it AND it's provided
        if model_schema.capabilities.supports_negative_prompt and request.negative_prompt is not None:
            request_params["negative_prompt"] = request.negative_prompt
        # Only include lora parameters if model supports it AND they're provided
        if model_schema.capabilities.supports_lora and request.lora_scale is not None and request.lora_scale > 0:
            request_params["lora_scale"] = request.lora_scale
            request_params["lora_url"] = request.lora_url or self.settings.lora_url

        # Build API parameters using model schema
        generate_params = model_schema.build_api_params(request_params)

        logger.info(f"Calling Together API with model: {model}")
        logger.debug(f"API parameters: {generate_params}")
        
        # Verify API key is set
        if not self.settings.api_key or self.settings.api_key.strip() == "":
            raise ValueError("TOGETHER_API_KEY is not set or empty")
        
        try:
            # Use direct HTTP call to have full control over parameters
            # This bypasses the Together SDK which might be adding unwanted defaults
            logger.info("Waiting for Together API response (timeout: 300s)...")
            
            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.post(
                    "https://api.together.xyz/v1/images/generations",
                    headers={
                        "Authorization": f"Bearer {self.settings.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=generate_params,
                )
                response.raise_for_status()
                result = response.json()
            
            logger.info(f"Together API call successful, received response")
            
            if not result or "data" not in result:
                raise ValueError("Invalid response structure from API")
                
            if not result["data"] or len(result["data"]) == 0:
                raise ValueError("No image data in API response")
                
            image_data = result["data"][0]
            
            # Handle both b64_json and base64 response formats
            b64 = None
            if "b64_json" in image_data:
                b64 = image_data["b64_json"]
            elif "base64" in image_data:
                b64 = image_data["base64"]
            elif "url" in image_data:
                logger.warning("API returned URL instead of base64. This endpoint expects base64.")
                raise ValueError("API returned URL instead of base64. Please check response_format parameter.")
            else:
                raise ValueError("Empty or missing base64 data in response")
                
            logger.info(f"Image generated successfully, base64 length: {len(b64)}")
            return b64.replace("\n", "")
            
        except asyncio.TimeoutError:
            logger.error("Together API call timed out after 300 seconds")
            logger.error("Possible causes: network issues, API overload, invalid API key, or model unavailable")
            raise Exception("Image generation timed out after 300 seconds (5 minutes). This may indicate network issues, API overload, or the model is unavailable. Please check your network connection, API key, and try again.")
        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e)
            logger.error(f"Error calling Together API: {error_type}: {error_msg}", exc_info=True)
            
            # Provide more helpful error messages
            if "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
                raise Exception(f"Request timed out. The Together API may be slow or overloaded. Error: {error_msg}")
            elif "401" in error_msg or "Unauthorized" in error_msg:
                raise Exception("Invalid API key. Please check your TOGETHER_API_KEY environment variable.")
            elif "429" in error_msg or "rate limit" in error_msg.lower():
                raise Exception("Rate limit exceeded. Please try again later.")
            elif "404" in error_msg or "not found" in error_msg.lower():
                raise Exception(f"Model '{model}' not found or unavailable. Please check the model name.")
            else:
                raise


@lru_cache(maxsize=1)
def get_together_client() -> TogetherClient:
    settings = TogetherSettings()
    return TogetherClient(settings)

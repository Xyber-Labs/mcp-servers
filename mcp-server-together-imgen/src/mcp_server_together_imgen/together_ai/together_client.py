import asyncio
from functools import lru_cache

from loguru import logger
from together import AsyncTogether

from mcp_server_together_imgen.together_ai.config import TogetherSettings
from mcp_server_together_imgen.schemas import ImageGenerationRequest


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
        use_lora = request.lora_scale is not None and request.lora_scale > 0

        if use_lora:
            model = self.settings.lora_image_model
            loras = [
                {"path": self.settings.lora_url, "scale": float(request.lora_scale)}
            ]
        else:
            model = self.settings.non_lora_image_model
            loras = None

        # FLUX.2 models don't support negative_prompt
        # FLUX.2-flex uses "guidance" parameter, not "guidance_scale"
        # FLUX.2-pro and FLUX.2-dev don't support guidance parameters
        # FLUX.1-dev and other models use "guidance_scale"
        is_flux2 = "FLUX.2" in model or "flux.2" in model.lower()
        is_flux2_flex = "flex" in model.lower()
        supports_guidance_scale = not is_flux2  # Only FLUX.1 and older models

        # Build the request parameters - match the working Together API example
        generate_params = {
            "model": model,
            "prompt": request.prompt,
            "n": 1,
        }
        
        # FLUX.2 models: add width/height if specified
        if request.width is not None:
            generate_params["width"] = request.width
        if request.height is not None:
            generate_params["height"] = request.height
        
        # Add optional parameters only if they have valid values
        if request.steps is not None:
            generate_params["steps"] = request.steps
        
        # Only include seed if it's not None and not 0 (some APIs don't accept 0)
        if request.seed is not None and request.seed != 0:
            generate_params["seed"] = request.seed
        
        # FLUX.2 models: disable safety checker (recommended for FLUX.2)
        if is_flux2:
            generate_params["disable_safety_checker"] = True
            # FLUX.2 requires explicit response_format to get base64
            generate_params["response_format"] = "b64_json"
        else:
            # For other models, use base64 format
            generate_params["response_format"] = "base64"
            if request.width is not None or request.height is not None:
                generate_params["output_format"] = "png"
        
        # Add LoRA support if applicable (for FLUX.1 models)
        if loras is not None:
            generate_params["image_loras"] = loras

        # FLUX.2 models don't support negative_prompt
        if not is_flux2 and request.negative_prompt is not None:
            generate_params["negative_prompt"] = request.negative_prompt

        # Add guidance parameter based on model type
        if is_flux2_flex and request.guidance_scale is not None:
            # FLUX.2-flex uses "guidance" parameter
            generate_params["guidance"] = request.guidance_scale
        elif supports_guidance_scale and request.guidance_scale is not None:
            # FLUX.1-dev and older models use "guidance_scale"
            generate_params["guidance_scale"] = request.guidance_scale

        logger.info(f"Calling Together API with model: {model}")
        logger.debug(f"API parameters: {generate_params}")
        
        # Verify API key is set
        if not self.settings.api_key or self.settings.api_key.strip() == "":
            raise ValueError("TOGETHER_API_KEY is not set or empty")
        
        try:
            # Add timeout of 300 seconds (FLUX.2 can take 60-180+ seconds for high quality)
            # This matches the client-level timeout
            logger.info("Waiting for Together API response (timeout: 300s)...")
            response = await asyncio.wait_for(
                self.client.images.generate(**generate_params),
                timeout=300.0
            )
            logger.info(f"Together API call successful, received response")
            
            if not response or not hasattr(response, 'data'):
                raise ValueError("Invalid response structure from API")
                
            if not response.data or len(response.data) == 0:
                raise ValueError("No image data in API response")
                
            image_data = response.data[0]
            if not hasattr(image_data, 'b64_json') or not image_data.b64_json:
                # Check if URL is returned instead
                if hasattr(image_data, 'url') and image_data.url:
                    logger.warning("API returned URL instead of base64. This endpoint expects base64.")
                    raise ValueError("API returned URL instead of base64. Please check response_format parameter.")
                raise ValueError("Empty or missing base64 data in response")
                
            b64 = image_data.b64_json
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

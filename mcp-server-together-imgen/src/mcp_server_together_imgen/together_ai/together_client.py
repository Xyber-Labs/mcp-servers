from functools import lru_cache

from loguru import logger
from together import AsyncTogether

from mcp_server_together_imgen.together_ai.config import TogetherSettings
from mcp_server_together_imgen.schemas import ImageGenerationRequest


class TogetherClient:
    def __init__(self, settings: TogetherSettings):
        self.settings = settings
        self.client = AsyncTogether(api_key=self.settings.api_key)

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

        # FLUX.2-pro and similar models don't support guidance_scale
        # Only include it for models that support it (e.g., FLUX.1-dev)
        supports_guidance_scale = "FLUX.2" not in model and "flux.2" not in model.lower()

        # Build the request parameters
        generate_params = {
            "model": model,
            "prompt": request.prompt,
            "negative_prompt": request.negative_prompt,
            "width": request.width,
            "height": request.height,
            "steps": request.steps,
            "seed": request.seed,
            "n": 1,
            "response_format": "base64",
            "output_format": "png",
            "image_loras": loras,
        }

        # Only add guidance_scale if the model supports it
        if supports_guidance_scale and request.guidance_scale is not None:
            generate_params["guidance_scale"] = request.guidance_scale

        response = await self.client.images.generate(**generate_params)
        b64 = response.data[0].b64_json
        return b64.replace("\n", "")


@lru_cache(maxsize=1)
def get_together_client() -> TogetherClient:
    settings = TogetherSettings()
    return TogetherClient(settings)

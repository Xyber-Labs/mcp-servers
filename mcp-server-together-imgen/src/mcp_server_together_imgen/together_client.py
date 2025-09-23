from functools import lru_cache

from loguru import logger
from together import AsyncTogether

from mcp_server_together_imgen.config import TogetherSettings
from mcp_server_together_imgen.schemas import ImageGenerationRequest

INSTRUCTION_TEXT = """
<instruction>
Your task is to slightly rewrite the user's prompt so FLUX.1-dev better understands the visual intent.
We use a LoRA trained for a [young woman with short, light blue hair], and the user's prompt is about her.
If the user didn't specify, add or (if specified) refine these details briefly:
- Character: [young woman with short, light blue hair]
- Lighting
- Background (e.g., futuristic gaming room; white walls, high ceiling)
- Camera view (vary: selfie, front, etc.)
- Emotion (sad, angry, etc.)
- Style: 3D CGI
- Clothes (e.g., silver jacket with triangle cut-out; or yellow/orange jacket with triangle)
- 4K, high consistency, amazing quality
- Age: ~18–20 (crucial)
NO commentary. Output ONLY the final prompt, max ~100 tokens.
Here is the user prompt:
"""


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
                    {"role": "user", "content": INSTRUCTION_TEXT + user_prompt},
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
        loras = (
            [{"path": request.lora_url, "scale": request.lora_scale}]
            if request.lora_url and request.lora_scale is not None
            else []
        )

        response = await self.client.images.generate(
            model=self.settings.image_model,
            prompt=request.prompt,
            width=request.width,
            height=request.height,
            steps=request.steps,
            guidance_scale=request.guidance_scale,
            seed=request.seed,
            n=1,
            response_format="base64",
            output_format="png",
            image_loras=loras,
        )
        b64 = response.data[0].b64_json
        return b64.replace("\n", "")


@lru_cache(maxsize=1)
def get_together_client() -> TogetherClient:
    settings = TogetherSettings()
    return TogetherClient(settings)

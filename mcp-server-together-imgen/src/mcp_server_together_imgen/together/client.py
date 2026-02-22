from typing import Literal

import httpx
from loguru import logger

from mcp_server_together_imgen.together.config import TogetherSettings


class TogetherClient:
    def __init__(self, settings: TogetherSettings):
        self.settings = settings

    async def generate_image(
        self,
        prompt: str,
        model: str | None = None,
        width: int = 1024,
        height: int = 1024,
        steps: int | None = None,
        guidance_scale: float | None = None,
        negative_prompt: str | None = None,
        seed: int | None = None,
    ) -> str:
        """Generate image and return base64 string."""
        model = model or self.settings.default_model

        # Build API parameters
        api_params = {
            "model": model,
            "prompt": prompt,
            "width": width,
            "height": height,
            "n": 1,
            "response_format": "base64",
        }

        # Add optional parameters if provided
        if steps is not None:
            api_params["steps"] = steps
        if guidance_scale is not None:
            api_params["guidance_scale"] = guidance_scale
        if negative_prompt is not None:
            api_params["negative_prompt"] = negative_prompt
        if seed is not None and seed != 0:
            api_params["seed"] = seed

        logger.info(f"Generating image with model: {model}")
        logger.debug(f"API parameters: {api_params}")

        return await self._call_image_api(api_params, model)

    async def generate_image_with_lora(
        self,
        prompt: str,
        lora_url: str,
        lora_scale: float = 1.0,
        model: str | None = None,
        width: int = 1024,
        height: int = 1024,
        steps: int | None = None,
        guidance_scale: float | None = None,
        seed: int | None = None,
    ) -> str:
        """Generate image with LoRA adapter, return base64 string."""
        model = model or self.settings.lora_model

        # Build API parameters with LoRA
        api_params = {
            "model": model,
            "prompt": prompt,
            "width": width,
            "height": height,
            "n": 1,
            "response_format": "base64",
            "image_loras": [
                {
                    "path": lora_url,
                    "scale": float(lora_scale),
                }
            ],
        }

        # Add optional parameters if provided
        if steps is not None:
            api_params["steps"] = steps
        if guidance_scale is not None:
            api_params["guidance_scale"] = guidance_scale
        if seed is not None and seed != 0:
            api_params["seed"] = seed

        logger.info(f"Generating image with LoRA using model: {model}")
        logger.debug(f"API parameters: {api_params}")
        logger.debug(f"LoRA URL: {lora_url}, scale: {lora_scale}")

        return await self._call_image_api(api_params, model)

    async def refine_prompt(
        self, prompt: str, mode: Literal["standard", "lora"] = "standard"
    ) -> str:
        """Refine prompt using chat API with mode-specific instruction."""
        instruction = (
            self.settings.refine_prompt_standard
            if mode == "standard"
            else self.settings.refine_prompt_lora
        )

        try:
            logger.info(f"Refining prompt with mode: {mode}")
            async with httpx.AsyncClient(
                timeout=self.settings.generation_timeout
            ) as client:
                response = await client.post(
                    "https://api.together.xyz/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.settings.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.settings.refiner_model,
                        "messages": [
                            {
                                "role": "system",
                                "content": "You are a helpful prompt rewriter for image models.",
                            },
                            {
                                "role": "user",
                                "content": instruction + "\n\n" + prompt,
                            },
                        ],
                        "temperature": 0.2,
                    },
                )
                response.raise_for_status()
                result = response.json()

            refined = (result["choices"][0]["message"]["content"] or "").strip()
            logger.info(f"Prompt refined successfully")
            return refined or prompt

        except Exception as e:
            logger.error(f"Failed to refine prompt, falling back: {e}")
            return prompt

    async def _call_image_api(self, api_params: dict, model: str) -> str:
        """Internal method to call Together Images API and return base64 string."""
        # Verify API key is set
        if not self.settings.api_key or self.settings.api_key.strip() == "":
            raise ValueError("TOGETHER_API_KEY is not set or empty")

        try:
            logger.info(
                f"Waiting for Together API response (timeout: {self.settings.generation_timeout}s)..."
            )

            async with httpx.AsyncClient(
                timeout=self.settings.generation_timeout
            ) as client:
                response = await client.post(
                    "https://api.together.xyz/v1/images/generations",
                    headers={
                        "Authorization": f"Bearer {self.settings.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=api_params,
                )
                response.raise_for_status()
                result = response.json()

            logger.info("Together API call successful, received response")

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
                logger.warning(
                    "API returned URL instead of base64. This endpoint expects base64."
                )
                raise ValueError(
                    "API returned URL instead of base64. Please check response_format parameter."
                )
            else:
                raise ValueError("Empty or missing base64 data in response")

            logger.info(f"Image generated successfully, base64 length: {len(b64)}")
            return b64.replace("\n", "")

        except TimeoutError:
            logger.error(
                f"Together API call timed out after {self.settings.generation_timeout} seconds"
            )
            logger.error(
                "Possible causes: network issues, API overload, invalid API key, or model unavailable"
            )
            raise Exception(
                f"Image generation timed out after {self.settings.generation_timeout} seconds. "
                "This may indicate network issues, API overload, or the model is unavailable. "
                "Please check your network connection, API key, and try again."
            )
        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e)
            logger.error(
                f"Error calling Together API: {error_type}: {error_msg}", exc_info=True
            )

            # Provide more helpful error messages
            if "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
                raise Exception(
                    f"Request timed out. The Together API may be slow or overloaded. Error: {error_msg}"
                )
            elif "401" in error_msg or "Unauthorized" in error_msg:
                raise Exception(
                    "Invalid API key. Please check your TOGETHER_API_KEY environment variable."
                )
            elif "429" in error_msg or "rate limit" in error_msg.lower():
                raise Exception("Rate limit exceeded. Please try again later.")
            elif "404" in error_msg or "not found" in error_msg.lower():
                raise Exception(
                    f"Model '{model}' not found or unavailable. Please check the model name."
                )
            else:
                raise

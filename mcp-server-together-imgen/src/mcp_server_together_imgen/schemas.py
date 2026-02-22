from pydantic import BaseModel, ConfigDict, Field


class HealthCheckResponse(BaseModel):
    """Response schema for health check endpoint."""

    status: str = Field(..., description="The status of the server")
    service: str = Field(..., description="The name of the service")


class ImageResponse(BaseModel):
    """Response schema for image generation endpoints."""

    image_base64: str = Field(..., description="Base64-encoded generated image")
    model_used: str = Field(..., description="The model that was used for generation")
    refined_prompt: str | None = Field(
        None, description="The refined prompt if refine_prompt was enabled"
    )
    lora_url: str | None = Field(
        None, description="The LoRA URL if LoRA was used in generation"
    )


class ImageGenerationRequest(BaseModel):
    """
    Request schema for image generation with dynamic model support.

    Example request:
    {
        "prompt": "image of the car",
        "model": "black-forest-labs/FLUX.2-dev",
        "width": 1024,
        "height": 1024,
        "steps": 20
    }
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "prompt": "image of the car",
                "model": "black-forest-labs/FLUX.2-dev",
                "width": 1024,
                "height": 1024,
                "steps": 20,
                "guidance_scale": None,
                "seed": None,
                "lora_scale": 0,
                "lora_url": None,
                "negative_prompt": None,
                "refine_prompt": False,
            }
        }
    )

    prompt: str = Field(
        ...,
        description="REQUIRED: The text prompt describing the image you want to generate. This should be your image description, NOT a model name. Examples: 'image of the car', 'a beautiful sunset', 'a futuristic cityscape'",
        examples=[
            "image of the car",
            "a beautiful sunset over mountains",
            "a futuristic cityscape",
        ],
    )
    model: str | None = Field(
        None,
        description="OPTIONAL: The model to use for image generation. Must be a valid model name like 'black-forest-labs/FLUX.2-dev'. If not specified, uses the default model from environment. Common models: black-forest-labs/FLUX.1-dev, black-forest-labs/FLUX.1-dev-lora, black-forest-labs/FLUX.2-dev, black-forest-labs/FLUX.2-pro, black-forest-labs/FLUX.2-flex",
        examples=[
            "black-forest-labs/FLUX.2-dev",
            "black-forest-labs/FLUX.1-dev",
            "black-forest-labs/FLUX.2-pro",
        ],
    )
    width: int | None = Field(
        1024,
        ge=64,
        le=4096,
        multiple_of=8,
        description="The width of the image.",
    )
    height: int | None = Field(
        1024,
        ge=64,
        le=4096,
        multiple_of=8,
        description="The height of the image.",
    )
    steps: int | None = Field(
        20, ge=1, le=100, description="The number of generation steps."
    )
    guidance_scale: float | None = Field(
        None,
        ge=1.0,
        le=30.0,
        description="The guidance scale. Supported for FLUX.1-dev and FLUX.2-flex models. Not supported for FLUX.2-pro/dev.",
    )
    seed: int | None = Field(
        None,
        description="The seed for the generation. Use null (not 0) or omit for random seed. Note: seed=0 may not be accepted by some models.",
        examples=[None, 12345, 42],
    )
    lora_scale: float | None = Field(
        0.0,
        ge=0.0,
        le=1.0,
        description="LoRA scale; 0 disables LoRA. Only supported for FLUX.1-dev-lora models.",
    )
    lora_url: str | None = Field(
        None,
        description="LoRA URL. Required if lora_scale > 0 for FLUX.1-dev-lora models.",
        examples=[None, "https://huggingface.co/<your-account>/<lora-adapter-link>"],
    )
    negative_prompt: str | None = Field(
        None,
        description="The prompt or prompts not to guide the image generation. Only supported for FLUX.1-dev and older models. Not supported for FLUX.2 models. Use null for FLUX.2 models.",
        examples=[None, "blurry, low quality"],
    )
    refine_prompt: bool = Field(
        False,
        description="Whether to refine the prompt using a chat model.",
    )


from pydantic import BaseModel, Field


class ImageGenerationRequest(BaseModel):
    prompt: str = Field(..., description="The text prompt to generate the image from.")
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
        description="The guidance scale. Only supported for FLUX.1-dev and FLUX.2-flex models. Not supported for FLUX.2-pro/dev."
    )
    seed: int | None = Field(
        None, 
        description="The seed for the generation. Use None or omit for random seed. Note: seed=0 may not be accepted by some models."
    )
    lora_scale: float | None = Field(
        0.0, 
        ge=0.0, 
        le=1.0, 
        description="LoRA scale; 0 disables LoRA. Only supported for FLUX.1-dev-lora models."
    )
    negative_prompt: str | None = Field(
        None, 
        description="The prompt or prompts not to guide the image generation. Only supported for FLUX.1-dev and older models. Not supported for FLUX.2 models."
    )
    refine_prompt: bool = Field(
        False,
        description="Whether to refine the prompt using a chat model.",
    )
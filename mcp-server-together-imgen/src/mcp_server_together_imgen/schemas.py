from pydantic import BaseModel, Field


class ImageGenerationRequest(BaseModel):
    prompt: str = Field(..., description="The text prompt to generate the image from.")
    width: int | None = Field(1024, description="The width of the image.")
    height: int | None = Field(1024, description="The height of the image.")
    steps: int | None = Field(28, description="The number of generation steps.")
    guidance_scale: float | None = Field(3.5, description="The guidance scale.")
    seed: int | None = Field(42, description="The seed for the generation.")
    lora_url: str | None = Field(None, description="The URL of the LoRA model to use.")
    lora_scale: float | None = Field(0.9, description="The scale of the LoRA model.")
    refine_prompt: bool = Field(
        False,
        description="Whether to refine the prompt using a chat model.",
    )

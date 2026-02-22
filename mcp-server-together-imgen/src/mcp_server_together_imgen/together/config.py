from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class TogetherSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        populate_by_name=True,  # Allow using both field name and alias
    )

    # API key uses TOGETHER_API_KEY env var (supports both field and env name)
    api_key: str = Field(
        ..., validation_alias=AliasChoices("api_key", "TOGETHER_API_KEY")
    )

    # Default models - support both field names and legacy env var names
    default_model: str = Field(
        "black-forest-labs/FLUX.1-dev",
        validation_alias=AliasChoices("default_model", "NON_LORA_IMAGE_MODEL"),
    )
    lora_model: str = Field(
        "black-forest-labs/FLUX.1-dev-lora",
        validation_alias=AliasChoices("lora_model", "LORA_IMAGE_MODEL"),
    )
    refiner_model: str = Field(
        "deepseek-ai/DeepSeek-V3",
        validation_alias=AliasChoices("refiner_model", "REFINER_MODEL"),
    )

    # Default LoRA URL (can be overridden per request)
    # If not set, the LoRA endpoint will require lora_url to be provided in each request
    lora_url: str | None = Field(
        None,
        validation_alias=AliasChoices("lora_url", "LORA_URL"),
    )

    # Prompt refinement instructions (two separate prompts for different endpoints)
    refine_prompt_standard: str = Field(
        "Rewrite this prompt for FLUX image generation, maintaining the core concept but improving clarity and detail.",
        validation_alias=AliasChoices("refine_prompt_standard", "REFINE_PROMPT_STANDARD"),
    )
    refine_prompt_lora: str = Field(
        "<instruction>Your task is to slightly rewrite a user's prompt for an image generation request. The image generation model has been fine-tuned using a specific dataset (LoRA adapter), so your job is to subtly adjust the language to better align with that fine-tuned style while preserving the user's core intent.</instruction>",
        validation_alias=AliasChoices("refine_prompt_lora", "REFINE_PROMPT_LORA"),
    )

    # Timeouts
    generation_timeout: int = 300  # 5 minutes for FLUX.2

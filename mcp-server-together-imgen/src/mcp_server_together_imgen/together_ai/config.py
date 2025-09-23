from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class TogetherSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    api_key: str = Field(..., alias="TOGETHER_API_KEY")
    refiner_model: str = Field("deepseek-ai/DeepSeek-V3", alias="REFINER_MODEL")
    image_model: str = Field(
        "black-forest-labs/FLUX.1-dev-lora", alias="IMAGE_MODEL"
    )
    lora_url: str = Field(
        "https://huggingface.co/ExplosionNuclear/Lumira-3-New", alias="LORA_URL"
    )
    instruction_text: str | None = Field(
        None,
        alias="INSTRUCTION_TEXT",
    )

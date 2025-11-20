from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class TavilyConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="TAVILY_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    api_key: str = Field(default="")

    max_results: int = Field(default=5, ge=1)
    topic: str = "general"
    search_depth: str = Field(default="basic", pattern="^(basic|advanced)$")
    include_answer: bool = False
    include_raw_content: bool = False
    include_images: bool = False

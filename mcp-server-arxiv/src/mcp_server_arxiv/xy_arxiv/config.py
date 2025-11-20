from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ArxivConfig(BaseSettings):
    """
    Configuration for the ArXiv Search Service.
    Reads from environment variables prefixed with ARXIV_.
    """

    model_config = SettingsConfigDict(
        env_prefix="ARXIV_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    max_results: int = Field(default=5, ge=1, le=50)
    max_text_length: int | None = Field(
        default=None, ge=100
    )

@lru_cache(maxsize=1)
def get_arxiv_config() -> ArxivConfig:
    """
    Get a cached instance of ArxivConfig.
    """
    config = ArxivConfig()
    return config

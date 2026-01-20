import os
import logging

from dotenv import load_dotenv
from pydantic import BaseModel
from typing import Optional
from pydantic import Field
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)
from pathlib import Path

logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()
# Define the path to the root .env file to ensure consistent loading
_project_root = Path(__file__).resolve().parent.parent
_env_file = _project_root / ".env"


# Database configuration
class DatabaseConfig(BaseModel):
    """Database configuration for Postgres cache."""

    DB_NAME: str = os.getenv("DB_NAME", "mcp_deep_research_postgres")
    DB_USER: str = os.getenv("DB_USER", "postgres")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "postgres")
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT_RAW: str = os.getenv("DB_PORT", "5432")
    DB_PORT: str = (
        DB_PORT_RAW.split(":")[0] if ":" in DB_PORT_RAW else DB_PORT_RAW
    )
    DATABASE_URL: str = (
        f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )
    logger.info(f"DEBUG: Connecting to: {DATABASE_URL}")


class LLM_Config(BaseModel):
    """Configuration settings for the LLMs."""

    TOGETHER_API_KEY: str = os.getenv("TOGETHER_API_KEY")
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY")
    MISTRAL_API_KEY: str = os.getenv("MISTRAL_API_KEY")
    MODEL_PROVIDER: str = "google"
    MODEL_NAME: str = "gemini-2.0-flash"
    MODEL_PROVIDER_SPARE: str = "google"
    MODEL_NAME_SPARE: str = "gemini-2.0-flash"
    MODEL_PROVIDER_THINKING: Optional[str] = "google"
    MODEL_NAME_THINKING: Optional[str] = "gemini-2.5-pro"
    MODEL_VALIDATION_PROVIDER: Optional[str] = "google"
    MODEL_VALIDATION_NAME: Optional[str] = "gemini-2.0-flash"


class DeepResearcherConfig(BaseModel):
    """Configuration settings for the Deep Researcher."""
    MAX_WEB_RESEARCH_LOOPS: int = Field(default=3, ge=1, le=10, description="Maximum number of web research loops to perform (1-10)")


class SearchMCP_Config(BaseModel):
    """Configuration settings for the dependent search MCP servers."""
    APIFY_TOKEN: Optional[str] = os.getenv("APIFY_TOKEN")
    MCP_TAVILY_URL: str = os.getenv("MCP_TAVILY_URL")
    MCP_ARXIV_URL: str = os.getenv("MCP_ARXIV_URL")
    MCP_TWITTER_APIFY_URL: str = os.getenv("MCP_TWITTER_APIFY_URL")
    # Support both MCP_YOUTUBE_URL and MCP_YOUTUBE_APIFY_URL for backward compatibility
    MCP_YOUTUBE_APIFY_URL: str = os.getenv("MCP_YOUTUBE_APIFY_URL") or os.getenv("MCP_YOUTUBE_URL")
    MCP_TELEGRAM_PARSER_URL: Optional[str] = os.getenv("MCP_TELEGRAM_PARSER_URL")
    MCP_DEEPRESEARCH_URL: Optional[str] = os.getenv("MCP_DEEPRESEARCH_URL")



class LangfuseConfig(BaseSettings):
    """Configuration settings for Langfuse integration."""
    # Support both LANGFUSE_API_KEY and LANGFUSE_PUBLIC_KEY for compatibility
    LANGFUSE_API_KEY: str = Field(default="")
    LANGFUSE_SECRET_KEY: str = Field(default="")
    LANGFUSE_PROJECT: str = Field(default="deepresearcher")
    # Support both LANGFUSE_HOST and LANGFUSE_BASE_URL for compatibility
    LANGFUSE_HOST: str = Field(default="https://cloud.langfuse.com")
    
    model_config = SettingsConfigDict(
        env_file=_env_file,
        env_file_encoding="utf-8",
        extra="ignore",
    )
    
    def __init__(self, **kwargs):
        # Handle LANGFUSE_PUBLIC_KEY as alias for LANGFUSE_API_KEY
        if not kwargs.get("LANGFUSE_API_KEY"):
            api_key = os.getenv("LANGFUSE_API_KEY") or os.getenv("LANGFUSE_PUBLIC_KEY") or ""
            if api_key:
                kwargs["LANGFUSE_API_KEY"] = api_key
        # Handle LANGFUSE_BASE_URL as alias for LANGFUSE_HOST
        if not kwargs.get("LANGFUSE_HOST"):
            host = os.getenv("LANGFUSE_HOST") or os.getenv("LANGFUSE_BASE_URL") or "https://cloud.langfuse.com"
            kwargs["LANGFUSE_HOST"] = host
        super().__init__(**kwargs)



class Settings(BaseSettings):
    # For host-container path mapping
    MEDIA_HOST_DIR: Optional[str] = Field(default=None)

    # API Keys
    GOOGLE_API_KEY: str | None = Field(default=None)
    TAVILY_API_KEY: str | None = Field(default=None)
    MISTRAL_API_KEY: str | None = Field(default=None)
    TOGETHER_API_KEY: str | None = Field(default=None)
    APIFY_TOKEN: str | None = Field(default=None)

    langfuse: LangfuseConfig = LangfuseConfig()
    search_mcp: SearchMCP_Config = SearchMCP_Config()
    llm: LLM_Config = LLM_Config()
    database: DatabaseConfig = DatabaseConfig()
    model_config = SettingsConfigDict(
        env_file=_env_file,
        env_file_encoding="utf-8",
        extra="ignore",
        # BaseSettings automatically reads from env vars matching field names
        # No need for explicit env parameter in Field()
    )


# Global settings instance
settings = Settings()

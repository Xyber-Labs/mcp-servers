import logging
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

_ENV_PREFIX = "MCP_DEEP_RESEARCHER_"


class DatabaseConfig(BaseSettings):
    """Database configuration for Postgres (optional)."""

    model_config = SettingsConfigDict(
        env_prefix=_ENV_PREFIX,
        env_file=".env",
        extra="ignore",
    )

    db_name: str | None = None
    db_user: str | None = None
    db_password: str | None = None
    db_host: str | None = None
    db_port: int | None = None

    @property
    def is_configured(self) -> bool:
        """Check if all required database fields are set."""
        return all([self.db_name, self.db_user, self.db_password, self.db_host, self.db_port])

    @property
    def url(self) -> str | None:
        """Build database URL, or None if not fully configured."""
        if not self.is_configured:
            return None
        return f"postgresql+psycopg2://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"


class LLMConfig(BaseSettings):
    """LLM configuration using Xyber SDK SupportedModels enum values."""

    model_config = SettingsConfigDict(
        env_prefix=_ENV_PREFIX,
        env_file=".env",
        extra="ignore",
    )

    llm_main: str = Field(default="GEMINI_2_0_FLASH")
    llm_spare: str | None = Field(default=None)
    llm_thinking: str | None = Field(default=None)
    llm_validation: str | None = Field(default=None)


class ResearcherConfig(BaseSettings):
    """Deep Researcher agent settings."""

    model_config = SettingsConfigDict(
        env_prefix=_ENV_PREFIX,
        env_file=".env",
        extra="ignore",
    )

    max_web_research_loops: int = Field(default=3, ge=1, le=10)


class LangfuseConfig(BaseSettings):
    """Langfuse observability."""

    model_config = SettingsConfigDict(
        env_prefix="LANGFUSE_",
        env_file=".env",
        extra="ignore",
    )

    api_key: str = Field(default="")
    secret_key: str = Field(default="")
    host: str = Field(default="https://cloud.langfuse.com")
    project: str = Field(default="deepresearch")

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.secret_key)


# Cached config instances
@lru_cache(maxsize=1)
def get_database_config() -> DatabaseConfig:
    return DatabaseConfig()


@lru_cache(maxsize=1)
def get_llm_config() -> LLMConfig:
    return LLMConfig()


@lru_cache(maxsize=1)
def get_researcher_config() -> ResearcherConfig:
    return ResearcherConfig()


@lru_cache(maxsize=1)
def get_langfuse_config() -> LangfuseConfig:
    return LangfuseConfig()

"""Typed application settings loaded from environment variables / .env."""

from enum import StrEnum
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    DEVELOPMENT = "development"
    TEST = "test"
    PRODUCTION = "production"


class LLMProviderName(StrEnum):
    GEMINI = "gemini"
    OLLAMA = "ollama"
    BEDROCK = "bedrock"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    tejasri_env: Environment = Environment.DEVELOPMENT
    tejasri_log_level: str = "INFO"

    # Database (CockroachDB)
    database_url: str = "postgresql://root@localhost:26257/defaultdb?sslmode=disable"

    # LLM providers
    llm_provider: LLMProviderName = LLMProviderName.GEMINI
    gemini_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"

    # Auth
    jwt_secret_key: str = Field(default="", repr=False)
    jwt_access_token_minutes: int = 30

    # AWS
    aws_region: str = "ap-south-1"
    s3_bucket: str = ""

    @property
    def is_production(self) -> bool:
        return self.tejasri_env is Environment.PRODUCTION


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings singleton."""
    return Settings()

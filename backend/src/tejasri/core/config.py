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


class EmbeddingProviderName(StrEnum):
    HASH = "hash"  # deterministic, dependency-free (default for dev/CI)
    LOCAL = "local"  # sentence-transformers bge-small (optional extra)
    GEMINI = "gemini"  # hosted, truncated to 384 dims


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
    llm_failover: bool = True  # fall back to Ollama on primary failure
    gemini_api_key: str = Field(default="", repr=False)
    gemini_model: str = "gemini-2.0-flash"
    gemini_embedding_model: str = "text-embedding-004"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    bedrock_model: str = "anthropic.claude-3-haiku-20240307-v1:0"

    # Embeddings (load-bearing memory — deterministic by default, ADR 0003)
    embedding_provider: EmbeddingProviderName = EmbeddingProviderName.HASH

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

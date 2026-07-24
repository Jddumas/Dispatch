"""Central configuration and helpers for the Dispatch AI backend."""

from __future__ import annotations

import logging
import os

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class _Settings(BaseSettings):
    """Application settings loaded from environment or .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM settings
    llm_model: str = Field(default="llama3.1", alias="LLM_MODEL")
    classify_model: str | None = Field(default=None, alias="CLASSIFY_MODEL")
    embed_model: str = Field(default="nomic-embed-text", alias="EMBED_MODEL")
    ollama_host: str = Field(default="http://localhost:11434", alias="OLLAMA_HOST")

    # Persistence and guardrails
    checkpoint_db: str = Field(default="data/checkpoints.sqlite", alias="CHECKPOINT_DB")
    max_input_length: int = Field(default=2000, alias="MAX_INPUT_LENGTH")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # FastAPI settings
    api_rate_limit: str = Field(default="10/minute", alias="API_RATE_LIMIT")
    cors_origins: str = Field(default="*", alias="CORS_ORIGINS")
    token_cost_per_1k: float = Field(default=0.0, alias="TOKEN_COST_PER_1K")

    # LangSmith tracing
    langchain_tracing_v2: bool = Field(default=False, alias="LANGCHAIN_TRACING_V2")
    langchain_api_key: str | None = Field(default=None, alias="LANGCHAIN_API_KEY")
    langchain_project: str = Field(default="dispatch-ai", alias="LANGCHAIN_PROJECT")


settings = _Settings()

# Module-level constants for convenience.
LLM_MODEL = settings.llm_model
CLASSIFY_MODEL = settings.classify_model or settings.llm_model
EMBED_MODEL = settings.embed_model
OLLAMA_HOST = settings.ollama_host

CHECKPOINT_DB = settings.checkpoint_db
MAX_INPUT_LENGTH = settings.max_input_length

API_RATE_LIMIT = settings.api_rate_limit
CORS_ORIGINS = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]
TOKEN_COST_PER_1K = settings.token_cost_per_1k

# Propagate LangSmith settings to the environment so LangChain tracers pick them up.
if settings.langchain_api_key:
    os.environ.setdefault("LANGCHAIN_API_KEY", settings.langchain_api_key)
if settings.langchain_project:
    os.environ.setdefault("LANGCHAIN_PROJECT", settings.langchain_project)
if settings.langchain_tracing_v2:
    os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")


def setup_logging(level: int | str | None = None) -> None:
    """Configure the root logger for the project."""
    if level is None:
        level = os.getenv("LOG_LEVEL", settings.log_level)
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

"""Application configuration utilities."""

from functools import lru_cache
from pathlib import Path
from typing import Literal, Optional

from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly typed settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    app_name: str = Field(
        default="Multi-Agent Research Demo Backend",
        description="Human-readable application name.",
    )
    environment: Literal["local", "staging", "production"] = Field(
        default="local",
        description="Deployment environment indicator used for logging and metrics.",
    )
    log_level: str = Field(
        default="INFO",
        validation_alias="LOG_LEVEL",
        description="Python logging level for the service.",
    )

    openai_api_key: str = Field(
        alias="OPENAI_API_KEY",
        description="API key for the OpenAI-compatible endpoint defined in the article requirements.",
    )
    openai_model: str = Field(
        alias="OPENAI_MODEL",
        default="gpt-4o-mini",
        description="Default model identifier for LLM calls.",
    )
    openai_base_url: HttpUrl = Field(
        alias="OPENAI_BASE_URL",
        description="Base URL for the OpenAI-compatible API (e.g., SiliconFlow proxy).",
    )
    openai_temperature: float = Field(
        alias="OPENAI_TEMPERATURE",
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Default sampling temperature for agents.",
    )
    max_tokens: int = Field(
        alias="MAX_TOKENS",
        default=1024,
        gt=0,
        description="Max response tokens for primary LLM calls.",
    )

    # Backend runtime configuration
    run_retention_minutes: int = Field(
        default=120,
        ge=1,
        description="How long (in minutes) to retain completed run metadata in memory.",
    )
    agent_max_parallel_tasks: int = Field(
        default=5,
        ge=1,
        description="Maximum parallel subagents spawned by the lead agent as guided by the article heuristics.",
    )
    event_buffer_size: int = Field(
        default=1000,
        ge=100,
        description="Circular buffer size for run event logs streamed to the UI.",
    )
    citation_agent_enabled: bool = Field(
        default=True,
        description="Toggle for the citation pass—useful for local demos without extra calls.",
    )
    demo_seed_data_path: Optional[Path] = Field(
        default=None,
        description="Optional path to JSON/CSV fixtures used by offline research simulations.",
    )
    tavily_api_key: str = Field(
        alias="TAVILY_API_KEY",
        default="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",
        description="API key for Tavily live search integration.",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached Settings instance to share across the app."""

    return Settings()  # type: ignore[arg-type]

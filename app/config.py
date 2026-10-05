"""Application configuration for local and production-style deployments.

All runtime configuration is loaded from environment variables (and the local
.env file during development). Secrets must never be committed to source
control.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Validated runtime configuration."""

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent.parent / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Multi-Agent SQL Data Analyst"
    app_version: str = "1.0.0"
    environment: str = "development"
    log_level: str = "INFO"
    log_format: str = "auto"
    request_logging: bool = True

    host: str = "0.0.0.0"
    port: int = 8000

    database_url: str = Field(
        ...,
        description="SQLAlchemy PostgreSQL connection URL.",
    )
    langgraph_checkpoint_db_url: str | None = Field(
        default=None,
        description="PostgreSQL URL used by LangGraph checkpoints.",
    )

    cors_origins: str = "http://localhost:5173"

    redis_url: str = "redis://localhost:6379/0"
    redis_cache_ttl_seconds: int = 300

    groq_api_key: str | None = None
    openai_api_key: str | None = None
    gemini_api_key: str | None = None
    tavily_api_key: str | None = None
    huggingfacehub_api_key: str | None = None

    langsmith_tracing: str | None = None
    langsmith_end_point: str | None = None
    langsmith_api_key: str | None = None
    langsmith_project: str | None = None

    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_pre_ping: bool = True

    @property
    def database_checkpoint_url(self) -> str:
        """Use the dedicated checkpoint URL when supplied, otherwise DB URL."""
        return self.langgraph_checkpoint_db_url or self.database_url

    @property
    def cors_origin_list(self) -> list[str]:
        """Return configured CORS origins as a normalized list."""
        return [
            origin.strip()
            for origin in self.cors_origins.split(",")
            if origin.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()

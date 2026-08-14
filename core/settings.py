"""Application configuration via pydantic-settings."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Global application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="WEBHOOK_",
        env_file=".env",
        env_file_encoding="utf-8",
        frozen=True,
    )

    # Worker pool
    worker_count: int = Field(default=4, ge=1, description="Number of async workers")
    queue_max_size: int = Field(default=1000, ge=10, description="Max events in queue")

    # Rate limiter (per target_url)
    rate_limit_rate: float = Field(default=10.0, gt=0, description="Tokens per second")
    rate_limit_capacity: int = Field(default=20, ge=1, description="Max bucket capacity")

    # Retry / Backoff
    max_retries: int = Field(default=3, ge=0, description="Default max retries")
    base_delay: float = Field(default=1.0, gt=0, description="Base delay for backoff (sec)")
    max_delay: float = Field(default=60.0, gt=0, description="Max delay for backoff (sec)")

    # HTTP client
    http_timeout: float = Field(default=10.0, gt=0, description="HTTP request timeout (sec)")

    # Dead Letter Queue
    dlq_file: str = Field(default="dlq.jsonl", description="DLQ JSON Lines file path")

    # Shutdown
    shutdown_timeout: float = Field(
        default=30.0, gt=0, description="Graceful shutdown timeout (sec)"
    )


settings = Settings()

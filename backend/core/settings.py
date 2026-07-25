from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "产品管理智能助手平台"
    app_version: str = "1.0.0"
    environment: str = "development"

    database_url: str = "postgresql+asyncpg://root:kkkcm520@localhost:5432/product_analysis"
    database_pool_size: int = Field(default=20, ge=1)
    database_max_overflow: int = Field(default=40, ge=0)
    checkpoint_database_url: str = (
        "postgresql://root:kkkcm520@localhost:5432/product_analysis"
    )

    redis_url: str = "redis://:kkkcm520@localhost:6379/0"
    celery_broker_url: str = "redis://:kkkcm520@localhost:6379/1"
    celery_result_backend: str = "redis://:kkkcm520@localhost:6379/2"

    llm_api_key: str | None = None
    llm_api_base_url: str = "https://api.anthropic.com"
    llm_default_model: str = "claude-opus-4-8"
    llm_default_model_version: str = "2026-07-24"
    llm_prompt_version: str = "v1"
    llm_default_temperature: float = Field(default=0.3, ge=0, le=0.3)
    llm_max_tokens: int = Field(default=4096, ge=1)
    llm_timeout_seconds: float = Field(default=120, gt=0)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

from functools import lru_cache

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="RESUME_AGENT_", env_file=".env", extra="ignore"
    )

    api_key: str = ""
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-chat"
    timeout_seconds: int = Field(default=180, ge=10, le=600)
    hiring_threshold: int = Field(default=85, ge=0, le=100)
    max_iterations: int = Field(default=2, ge=0, le=5)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    log_file: str = "agent/data/logs/resume-agent.log"
    log_max_bytes: int = Field(default=10_000_000, ge=100_000)
    log_backup_count: int = Field(default=5, ge=1, le=20)


@lru_cache
def get_settings() -> Settings:
    return Settings()

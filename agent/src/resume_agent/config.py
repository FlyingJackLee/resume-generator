from functools import lru_cache

from typing import Literal

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Settings below only parses RESUME_AGENT_* keys out of .env into itself; it
# never touches os.environ. Libraries that read env vars directly (langsmith's
# LANGSMITH_TRACING/LANGSMITH_API_KEY/LANGSMITH_PROJECT, in particular) need
# them to actually land in the process environment, which `uv run` does not
# do by default.
load_dotenv()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="RESUME_AGENT_", env_file=".env", extra="ignore"
    )

    api_key: str = ""
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-chat"
    timeout_seconds: int = Field(default=180, ge=10, le=600)
    hiring_threshold: int = Field(default=75, ge=0, le=100)
    max_iterations: int = Field(default=2, ge=0, le=5)
    auto_approve_minutes: float = Field(default=5.0, ge=0)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    log_file: str = "agent/data/logs/resume-agent.log"
    log_max_bytes: int = Field(default=10_000_000, ge=100_000)
    log_backup_count: int = Field(default=5, ge=1, le=20)
    ocr_max_pages: int = Field(default=5, ge=1, le=20)
    scan_parser: Literal["rapidocr", "mineru_api"] = "rapidocr"
    mineru_api_base_url: str = "https://mineru.net/api/v4"
    mineru_api_token: str = ""
    mineru_model_version: Literal["pipeline", "vlm"] = "vlm"
    mineru_timeout_seconds: int = Field(default=180, ge=30, le=600)
    langsmith_project_url: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"
DEFAULT_FRONTEND_ORIGIN = "https://autonomous-decision-intelligence-en.vercel.app"
DEFAULT_VERCEL_ORIGIN_REGEX = r"^https://autonomous-decision-intelligence-en(?:-[a-z0-9-]+)?\.vercel\.app$"
DEFAULT_LOCAL_ORIGIN_REGEX = r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(ENV_FILE), env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite+aiosqlite:///./decision_intelligence.db"
    redis_url: str = "redis://localhost:6379/0"
    openai_api_key: str = ""
    clerk_secret_key: str = ""
    clerk_publishable_key: str = ""
    encryption_key: str = ""
    sentry_dsn: str = ""
    environment: str = "development"
    log_level: str = "INFO"
    allowed_origins: str = Field(
        default=f"http://localhost:3000,http://localhost:3002,http://localhost:3003,{DEFAULT_FRONTEND_ORIGIN}"
    )
    allowed_origin_regex: str = ""
    max_query_rows: int = 1000
    agent_max_iterations: int = 5
    rate_limit_requests: int = 20
    cache_ttl_schema: int = 3600
    cache_ttl_query: int = 300
    # Ollama is an opt-in local-LLM fallback tier. Leave empty to disable.
    # When set, the LLM service tries OpenAI first (if a key is present), then
    # this local endpoint, and finally the deterministic offline fallback.
    ollama_base_url: str = ""
    ollama_model: str = "llama3.2"
    # When true, row-level values are redacted (PII columns masked, long strings
    # truncated) before being serialized into LLM prompts.
    redact_pii_in_prompts: bool = True
    auth_bypass: bool = False
    # Directory where ingested dataset SQLite files are stored.
    uploads_dir: str = "./uploads"
    max_upload_bytes: int = 50 * 1024 * 1024  # 50 MB
    # Chroma vector store for RAG (optional). Leave chroma_host empty to use
    # the in-process fallback store.
    chroma_host: str = ""
    chroma_port: int = 8000

    @model_validator(mode="after")
    def parse_allowed_origins(self) -> "Settings":
        if isinstance(self.allowed_origins, str):
            self.allowed_origins = [
                origin.strip()
                for origin in self.allowed_origins.split(",")
                if origin.strip()
            ]
        if not self.allowed_origin_regex:
            if self.environment == "development":
                self.allowed_origin_regex = f"{DEFAULT_LOCAL_ORIGIN_REGEX}|{DEFAULT_VERCEL_ORIGIN_REGEX}"
            else:
                self.allowed_origin_regex = DEFAULT_VERCEL_ORIGIN_REGEX
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()

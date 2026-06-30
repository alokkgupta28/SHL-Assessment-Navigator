from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    catalog_path: str = "data/shl_catalog.json"
    allowed_origins: str = "http://localhost:5173,http://localhost:8080"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    cache_dir: str = "data/.cache"
    top_k_retrieval: int = 25
    top_k_final: int = 10
    log_level: str = "INFO"
    rate_limit_per_minute: int = 60
    rate_limit_burst: int = 20
    session_max: int = 5_000
    session_ttl_seconds: int = 3_600
    llm_timeout_seconds: float = 12.0


    @property
    def origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def catalog_file(self) -> Path:
        p = Path(self.catalog_path)
        if not p.is_absolute():
            p = Path(__file__).resolve().parent.parent / p
        return p

    @property
    def cache_path(self) -> Path:
        p = Path(self.cache_dir)
        if not p.is_absolute():
            p = Path(__file__).resolve().parent.parent / p
        p.mkdir(parents=True, exist_ok=True)
        return p


@lru_cache
def get_settings() -> Settings:
    return Settings()

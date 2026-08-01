"""Конфигурация приложения из локального .env — без секретов в коде."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_ROOT / ".env", extra="ignore")

    cpu_budget_fraction: float = 0.4
    database_dir: Path = BACKEND_ROOT / "data"
    models_dir: Path = BACKEND_ROOT.parent / "models"
    log_level: str = "INFO"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

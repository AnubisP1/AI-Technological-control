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

    # ⚠️ Осознанное исключение из офлайн-требования ТЗ (Фаза 8, см.
    # dev/QUESTIONS.md №12) — облачный YandexGPT API для формулировок
    # отчёта КД. Если не заданы, KdReviewService работает полностью
    # офлайн на шаблонном тексте (см. TemplateTextGenerator).
    yandex_gpt_api_key: str | None = None
    yandex_gpt_folder_id: str | None = None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

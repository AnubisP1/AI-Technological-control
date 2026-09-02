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

    # pythonocc-core (реальная тесселяция STEP -> mesh, Фаза 17 часть 5)
    # не публикуется на PyPI — доступен только через conda-forge, а
    # проект в остальном использует чистый venv+pip. Вместо перевода
    # всего backend на conda используется отдельное conda-окружение,
    # вызываемое как внешний интерпретатор через subprocess (тот же
    # принцип "внешняя dev/deploy-зависимость", что и для tesseract, см.
    # ocr_drawing_parser.py, только целый интерпретатор, а не бинарь в
    # PATH). Путь — абсолютный путь к python внутри conda-окружения,
    # НЕ угадывается автоматически (разные машины ставят conda в разные
    # места) — задаётся явно через .env; если не задан, реальная
    # тесселяция недоступна и PartViewer использует параметрический
    # прокси-бокс (см. STEP_MESH_UNAVAILABLE в step_mesh_exporter.py).
    pythonocc_python_path: Path | None = None

    # Локальный LLM (Фаза 18) — Qwen2.5-7B-Instruct, GGUF, через
    # llama-cpp-python, CPU-only. Заменяет прежний облачный YandexGPT-путь
    # (см. dev/QUESTIONS.md №12/№14) — полностью офлайн, вес модели
    # скачивается один раз при установке (см. dev/README.md), не в
    # рантайме. Путь не хардкодится и не угадывается — если не задан
    # или файл не существует, KdReviewService/AssistantService работают
    # полностью на шаблонном тексте (см. TemplateTextGenerator).
    llama_model_path: Path | None = None
    llama_context_size: int = 4096

    # Облачных LLM-провайдеров в этой сборке нет: контур dev_locall
    # работает строго офлайн (см. BRANCHES.md). Единственный LLM-путь —
    # локальный Qwen через llama.cpp, настраиваемый llama_model_path
    # выше; при отсутствии модели сервисы отвечают шаблонным текстом.


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

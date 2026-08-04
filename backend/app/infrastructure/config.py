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

    # ⚠️ Второй, облачный LLM-путь (Фаза 18, часть 2, см. dev/QUESTIONS.md
    # №15) — Polza.ai, OpenAI-совместимый API. Осознанное повторное
    # исключение из офлайн-требования ТЗ по прямому решению пользователя:
    # работает ПАРАЛЛЕЛЬНО локальному Qwen (приоритетнее в
    # _build_text_generator()/_build_chat_responder(), см. routes.py), не
    # заменяет его — локальный контур остаётся офлайн-путём для сценариев
    # без сети. Ключ — только через .env, никогда не в коде/гите.
    #
    # Модели заданы списком по приоритету, не одной константой: тариф
    # конкретного ключа может не давать доступ к произвольной модели
    # каталога (найдено на практике — qwen/qwen-2.5-7b-instruct отвечал
    # 403 FORBIDDEN с этим ключом, хотя был в /v1/models). Дефолт — две
    # модели, реально проверенные рабочими с этим ключом прямым curl-
    # запросом: openai/gpt-5.6-luna (чистый ответ без служебных reasoning-
    # токенов, предсказуемее для формулировки резюме) первой, затем
    # deepseek/deepseek-v4-flash-0731 (reasoning-модель — может отдать
    # часть лимита токенов на служебное "размышление", менее предсказуемо
    # для короткого ответа, поэтому вторая, не первая).
    polza_api_key: str | None = None
    polza_models: tuple[str, ...] = ("openai/gpt-5.6-luna", "deepseek/deepseek-v4-flash-0731")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

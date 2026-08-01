"""Точка входа FastAPI-приложения.

Ресурс-губернатор настраивается первым делом, до любых импортов,
которые могут потянуть torch/onnxruntime — многие такие библиотеки
читают переменные окружения (OMP_NUM_THREADS и т.д.) один раз при
собственном импорте.
"""

from app.infrastructure.resource_governor import configure as configure_resources
from app.infrastructure.config import get_settings

_settings = get_settings()
configure_resources(_settings.cpu_budget_fraction)

from fastapi import FastAPI  # noqa: E402  (после ресурс-губернатора)

from app.infrastructure.logging_setup import configure_logging  # noqa: E402
from app.api.routes import router as api_router  # noqa: E402

configure_logging(_settings.log_level)

app = FastAPI(title="Система анализа КД и генерации техпроцессов")
app.include_router(api_router)

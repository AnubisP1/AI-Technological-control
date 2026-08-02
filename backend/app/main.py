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
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from app.infrastructure.logging_setup import configure_logging  # noqa: E402
from app.api.routes import router as api_router  # noqa: E402

configure_logging(_settings.log_level)

app = FastAPI(title="Система анализа КД и генерации техпроцессов")

# Разрешаем оба локальных dev-фронтенда явными origin'ами (не "*") —
# dev/frontend (легаси, Фазы 0-8, порт 5173) и dev/frontend-v2 (Фаза 9+,
# порт 5174). Оба фронтенда также используют Vite dev-proxy для /api,
# так что CORS здесь — запасной путь, а не единственная защита.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

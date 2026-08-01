# Система анализа КД и генерации технологической документации

Локальное, полностью офлайн приложение: анализ конструкторской документации (чертёж/спецификация/STEP) и CAD-моделей, генерация маршрутной/операционной карты, симуляция изготовления и контроль качества. Полная бизнес-логика — в `../Техническое задание.md`; архитектурные решения и план — в `PLAN.md`, `PROGRESS.md`, `docs/`.

## Требования

- Python 3.11 (не выше — см. `docs/ARCHITECTURE.md`/`QUESTIONS.md` про совместимость с `pythonocc-core`)
- Node.js 20+ (проверено на 24)

## Backend

```bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env
python -m pytest -q              # тесты
uvicorn app.main:app --reload    # dev-сервер, http://localhost:8000/health
```

## База данных (НСИ)

```bash
cd backend
source .venv/bin/activate
python -c "
from pathlib import Path
from app.infrastructure.db.nsi_db import NsiDatabase, build_database
build_database(NsiDatabase.METAL, Path('data/metal.sqlite'))
build_database(NsiDatabase.ADDITIVE, Path('data/additive.sqlite'))
"
```

Создаёт два независимых SQLite-файла (металлообработка / аддитивные технологии) со схемой и демо-данными — адаптация PostgreSQL-схем из `../БД НСИ/` и `../БД НСИ Аддитив/`, см. `docs/ARCHITECTURE.md`.

## Frontend

```bash
cd frontend
npm install
npm run dev      # dev-сервер, http://localhost:5173
npm run build    # прод-сборка в dist/
```

## Офлайн-режим

Все зависимости ставятся один раз при наличии интернета (`pip install`, `npm install`). После установки приложение не обращается к сети — ни backend, ни frontend не используют CDN/облачные API в рантайме. Веса ML-моделей (когда появятся) будут храниться в `models/` и не должны требовать сети для загрузки после первого скачивания.

## Кроссплатформенность

Все пути в backend — через `pathlib.Path`, без хардкода `/` или `\`. Проверено на macOS; аналогичный набор команд должен работать на Windows без изменений (кроме активации venv — `.venv\Scripts\activate`).

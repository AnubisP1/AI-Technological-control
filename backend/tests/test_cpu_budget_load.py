"""Нагрузочный тест CPU-бюджета (ТЗ: не более 40-60% CPU), отложенный
с Фазы 0 (docs/PROGRESS.md) до появления реальной вычислительной нагрузки.
Парсинг STEP/PDF — первая такая нагрузка в проекте."""

from __future__ import annotations

import time
from pathlib import Path

import psutil
import pytest

from app.infrastructure.cad.pdf_drawing_parser import PdfDrawingParser
from app.infrastructure.cad.regex_step_parser import RegexStepParser
from app.infrastructure.resource_governor import configure

FIXTURES_ROOT = Path(__file__).resolve().parents[3] / "КД для тестов" / "Детали из металла"
VAL_DIR = FIXTURES_ROOT / "1. Тестовая деталь металл"
VAL_PDF = VAL_DIR / "К200-150-400ENERAL.20 - Вал.pdf"
VAL_STEP = VAL_DIR / "3D_К200-150-400 - Вал.stp"


def _require(path: Path) -> Path:
    if not path.exists():
        pytest.skip(f"fixture недоступен в этом окружении: {path}")
    return path


def test_step_and_drawing_parsing_respects_cpu_thread_budget():
    """Не измеряет системную загрузку CPU в процентах (что зависит от
    железа/шумных соседей в CI и нестабильно как assertion), а проверяет
    инвариант, который реально гарантирует соблюдение бюджета: процесс
    использует не больше потоков, чем разрешил ресурс-губернатор."""
    limits = configure()
    process = psutil.Process()

    drawing_path = _require(VAL_PDF)
    step_path = _require(VAL_STEP)

    threads_before = process.num_threads()
    started_at = time.time()

    PdfDrawingParser().parse(drawing_path)
    RegexStepParser().parse(step_path)

    elapsed = time.time() - started_at
    threads_after = process.num_threads()

    # Разбор не должен порождать пул потоков, конкурирующий с бюджетом
    # governor — сам парсинг однопоточный (regex/PyMuPDF в основном потоке).
    assert threads_after - threads_before <= limits.thread_count
    # Разбор одного файла должен быть быстрым (секунды, не минуты) —
    # грубая защита от случайной деградации (напр. катастрофического
    # backtracking в регулярном выражении на реальном файле).
    assert elapsed < 10.0

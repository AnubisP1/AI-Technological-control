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
from app.infrastructure.cad.step_feature_extractor import extract_step_topology
from app.infrastructure.cad.vector_view_detector import VectorViewDetector
from app.infrastructure.config import get_settings
from app.infrastructure.db.sqlite_process_planning_lookup import SqliteProcessPlanningLookup
from app.infrastructure.resource_governor import configure
from app.services.material_removal_simulator import simulate_material_removal
from app.services.toolpath_generator_service import ToolpathGeneratorService
from app.services.topology_feature_classifier import classify_topology

FIXTURES_ROOT = Path(__file__).resolve().parents[3] / "КД для тестов" / "Детали из металла"
VAL_DIR = FIXTURES_ROOT / "1. Тестовая деталь металл"
VAL_PDF = VAL_DIR / "К200-150-400ENERAL.20 - Вал.pdf"
VAL_STEP = VAL_DIR / "3D_К200-150-400 - Вал.stp"

LITERATURE_ROOT = Path(__file__).resolve().parents[3] / "Литература" / "НПО 2026"
BRACKET_STEP = LITERATURE_ROOT / "Кронштейн" / "Кронштейн.STEP"


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
    VectorViewDetector().detect(drawing_path)

    elapsed = time.time() - started_at
    threads_after = process.num_threads()

    # Разбор не должен порождать пул потоков, конкурирующий с бюджетом
    # governor — сам парсинг однопоточный (regex/PyMuPDF в основном потоке).
    assert threads_after - threads_before <= limits.thread_count
    # Разбор одного файла должен быть быстрым (секунды, не минуты) —
    # грубая защита от случайной деградации (напр. катастрофического
    # backtracking в регулярном выражении на реальном файле).
    assert elapsed < 10.0


def test_voxel_material_removal_simulation_respects_cpu_thread_budget():
    """Фаза 22 — voxel-симуляция съёма материала использует numpy
    (потенциально многопоточный BLAS/OMP), governor обязан ограничить
    число потоков так же, как и для остальных тяжёлых операций (см.
    resource_governor.configure() — устанавливает OMP_NUM_THREADS и
    аналоги ДО первого тяжёлого вызова numpy в процессе)."""
    settings = get_settings()
    if settings.pythonocc_python_path is None or not settings.pythonocc_python_path.exists():
        pytest.skip("PYTHONOCC_PYTHON_PATH не настроен в этом окружении")
    step_path = _require(BRACKET_STEP)

    db_path = Path(__file__).resolve().parents[1] / "data" / "metal.sqlite"
    if not db_path.exists():
        pytest.skip("data/metal.sqlite отсутствует в этом окружении")

    limits = configure()
    process = psutil.Process()

    topology = extract_step_topology(step_path, settings.pythonocc_python_path)
    features = classify_topology(topology)
    generator = ToolpathGeneratorService(SqliteProcessPlanningLookup(db_path))
    plan = generator.generate(
        part_name="Кронштейн", feature_set=features, material_group_id=5, bounding_box_mm=topology.bounding_box_mm
    )

    threads_before = process.num_threads()
    started_at = time.time()

    simulate_material_removal(plan)

    elapsed = time.time() - started_at
    threads_after = process.num_threads()

    assert threads_after - threads_before <= limits.thread_count
    assert elapsed < 10.0

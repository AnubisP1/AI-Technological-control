import math
import time
from pathlib import Path

import pytest

from app.domain.manufacturing.toolpath_model import ToolpathMove, ToolpathOperation, ToolpathPlan
from app.infrastructure.cad.step_feature_extractor import extract_step_topology
from app.infrastructure.config import get_settings
from app.infrastructure.db.sqlite_process_planning_lookup import SqliteProcessPlanningLookup
from app.services.material_removal_simulator import simulate_material_removal
from app.services.toolpath_generator_service import ToolpathGeneratorService
from app.services.topology_feature_classifier import classify_topology

LITERATURE_ROOT = Path(__file__).resolve().parents[3] / "Литература" / "НПО 2026"
BRACKET_STEP = LITERATURE_ROOT / "Кронштейн" / "Кронштейн.STEP"


def _require(path: Path) -> Path:
    if not path.exists():
        pytest.skip(f"fixture недоступен в этом окружении: {path}")
    return path


def _require_pythonocc() -> Path:
    python_path = get_settings().pythonocc_python_path
    if python_path is None or not python_path.exists():
        pytest.skip("PYTHONOCC_PYTHON_PATH не настроен в этом окружении")
    return python_path


def test_simulate_material_removal_on_real_bracket_toolpath_removes_plausible_fraction():
    """Реальный тулпас Кронштейна (facing + отверстие Ø25 через круговую
    интерполяцию) — удалённая доля объёма заготовки должна быть заметной,
    но не всей заготовкой целиком (иначе явный баг растеризации)."""
    python_path = _require_pythonocc()
    step_path = _require(BRACKET_STEP)

    topology = extract_step_topology(step_path, python_path)
    features = classify_topology(topology)
    db_path = Path(__file__).resolve().parents[1] / "data" / "metal.sqlite"
    if not db_path.exists():
        pytest.skip("data/metal.sqlite отсутствует в этом окружении")
    generator = ToolpathGeneratorService(SqliteProcessPlanningLookup(db_path))
    plan = generator.generate(
        part_name="Кронштейн",
        feature_set=features,
        material_group_id=5,  # ALUM
        bounding_box_mm=topology.bounding_box_mm,
    )

    simulation = simulate_material_removal(plan)

    total_voxels = simulation.grid.dims[0] * simulation.grid.dims[1] * simulation.grid.dims[2]
    removed_fraction = len(simulation.events) / total_voxels

    assert simulation.total_steps > 0
    assert len(simulation.events) > 0
    assert 0.01 < removed_fraction < 0.9
    # Каждое событие содержит валидный шаг и попадает в границы сетки.
    for event in simulation.events[:200]:  # не весь список — тысячи событий, достаточно выборки
        assert 0 <= event.voxel_x < simulation.grid.dims[0]
        assert 0 <= event.voxel_y < simulation.grid.dims[1]
        assert 0 <= event.voxel_z < simulation.grid.dims[2]
        assert 1 <= event.removed_at_step <= simulation.total_steps


def test_simulate_material_removal_runs_within_reasonable_time_budget():
    """CPU-бюджет проекта (≤40-60%) требует, чтобы одиночный расчёт
    симуляции укладывался в доли секунды — не абсолютная гарантия
    бюджета (это задача resource_governor на уровне процесса), но
    регрессионная защита от случайно квадратичного/экспоненциального
    алгоритма растеризации."""
    python_path = _require_pythonocc()
    step_path = _require(BRACKET_STEP)
    topology = extract_step_topology(step_path, python_path)
    features = classify_topology(topology)
    db_path = Path(__file__).resolve().parents[1] / "data" / "metal.sqlite"
    if not db_path.exists():
        pytest.skip("data/metal.sqlite отсутствует в этом окружении")
    generator = ToolpathGeneratorService(SqliteProcessPlanningLookup(db_path))
    plan = generator.generate(
        part_name="Кронштейн", feature_set=features, material_group_id=5, bounding_box_mm=topology.bounding_box_mm
    )

    start = time.monotonic()
    simulate_material_removal(plan)
    elapsed_seconds = time.monotonic() - start

    assert elapsed_seconds < 5.0


def test_simulate_material_removal_on_synthetic_single_straight_cut_removes_expected_region():
    """Синтетический план — один линейный рез фрезой Ø10 вдоль оси X по
    всей длине заготовки на определённой высоте Z — должен вырезать
    воксели вдоль этой линии и не тронуть воксели далеко от неё по Y."""
    plan = ToolpathPlan(
        part_name="Синтетическая плита",
        stock_bounding_box_mm=(0, 100, 0, 50, 0, 20),
        operations=(
            ToolpathOperation(
                sequence_no=1,
                feature_kind="facing",
                tool_diameter_mm=10.0,
                tool_designation="Тестовая фреза",
                spindle_speed_rpm=1000,
                feed_mm_min=200.0,
                moves=(
                    ToolpathMove(kind="rapid", x_mm=0, y_mm=25, z_mm=20),
                    ToolpathMove(kind="linear", x_mm=0, y_mm=25, z_mm=15, feed_mm_min=200),
                    ToolpathMove(kind="linear", x_mm=100, y_mm=25, z_mm=15, feed_mm_min=200),
                ),
                gcode_lines=("G1 X100 Y25 Z15",),
                estimated_time_min=1.0,
            ),
        ),
    )

    simulation = simulate_material_removal(plan)

    assert len(simulation.events) > 0

    # Воксель в углу заготовки, далеко от линии реза (y=0 угол, режущая
    # линия проходит по y=25 с радиусом 5мм) не должен быть удалён.
    removed_coords = {(e.voxel_x, e.voxel_y, e.voxel_z) for e in simulation.events}
    corner_voxel = (0, 0, simulation.grid.dims[2] - 1)  # верхний слой у дальнего угла
    assert corner_voxel not in removed_coords

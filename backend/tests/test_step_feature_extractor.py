from pathlib import Path

import pytest

from app.infrastructure.cad.step_feature_extractor import extract_step_topology
from app.infrastructure.config import get_settings

FIXTURES_ROOT = Path(__file__).resolve().parents[3] / "КД для тестов"
LITERATURE_ROOT = Path(__file__).resolve().parents[3] / "Литература" / "НПО 2026"

VAL_STEP = FIXTURES_ROOT / "Детали из металла" / "1. Тестовая деталь металл" / "3D_К200-150-400 - Вал.stp"
GEAR_STEP = (
    FIXTURES_ROOT
    / "Детали из металла"
    / "2. Тестовая деталь металл"
    / "Шестерня от конической передачи с круговым зубом редуктора TS 030411.04.950 _ KPP-5002-11.10.2024.stp"
)
BRACKET_STEP = LITERATURE_ROOT / "Кронштейн" / "Кронштейн.STEP"


def _require(path: Path) -> Path:
    if not path.exists():
        pytest.skip(f"fixture недоступен в этом окружении: {path}")
    return path


def _require_pythonocc() -> Path:
    python_path = get_settings().pythonocc_python_path
    if python_path is None or not python_path.exists():
        pytest.skip("PYTHONOCC_PYTHON_PATH не настроен в этом окружении — извлечение топологии недоступно")
    return python_path


def test_extract_topology_recognizes_bracket_geometry_on_real_fixture():
    """Кронштейн.STEP — независимо задокументированный fixture (см.
    Литература/НПО 2026/CLAUDE.md): алюминиевая плита, 20 граней, 6
    плоских, 4 галтели R10, 9 фасок, 1 сквозное отверстие Ø25. Числа
    здесь — не выдуманные ожидания, а факты, зафиксированные в CLAUDE.md
    соседнего проекта и независимо подтверждённые вручную при разработке
    (см. историю сессии Фазы 22)."""
    python_path = _require_pythonocc()
    step_path = _require(BRACKET_STEP)

    topology = extract_step_topology(step_path, python_path)

    assert topology is not None
    assert topology.total_face_count == 20
    assert len(topology.planar_faces) == 10
    assert len(topology.cylindrical_faces) == 5

    full_turn_cylinders = [c for c in topology.cylindrical_faces if c.is_full_turn]
    partial_cylinders = [c for c in topology.cylindrical_faces if not c.is_full_turn]

    # Ровно одно сквозное отверстие (Ø25 -> радиус 12.5) — отличено от
    # четырёх галтелей R10 по угловому охвату (see occ_feature_extract_script.py).
    assert len(full_turn_cylinders) == 1
    assert full_turn_cylinders[0].radius_mm == pytest.approx(12.5, abs=0.1)

    assert len(partial_cylinders) == 4
    for fillet in partial_cylinders:
        assert fillet.radius_mm == pytest.approx(10.0, abs=0.1)


def test_extract_topology_returns_none_when_python_path_missing():
    step_path = _require(BRACKET_STEP)
    assert extract_step_topology(step_path, None) is None


def test_extract_topology_returns_none_when_python_path_does_not_exist():
    step_path = _require(BRACKET_STEP)
    assert extract_step_topology(step_path, Path("/nonexistent/python")) is None


def test_extract_topology_handles_non_prismatic_shaft_without_crashing():
    """Вал — тело вращения, почти вся боковая поверхность цилиндрическая
    и полнооборотная (не отверстие, а сам вал) — extractor не обязан
    "понимать" эту деталь семантически, но обязан не падать и вернуть
    структуру, на которой дальнейший классификатор фич честно решит
    is_supported=False (см. TopologyFeatureClassifier)."""
    python_path = _require_pythonocc()
    step_path = _require(VAL_STEP)

    topology = extract_step_topology(step_path, python_path)

    assert topology is not None
    assert topology.total_face_count > 0


def test_extract_topology_handles_gear_without_crashing():
    python_path = _require_pythonocc()
    step_path = _require(GEAR_STEP)

    topology = extract_step_topology(step_path, python_path)

    assert topology is not None
    assert topology.total_face_count > 0

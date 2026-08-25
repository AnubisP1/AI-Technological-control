from pathlib import Path

import pytest

from app.domain.cad.feature_model import CylindricalFace, PartTopology, PlanarFace
from app.infrastructure.cad.step_feature_extractor import extract_step_topology
from app.infrastructure.config import get_settings
from app.services.topology_feature_classifier import classify_topology

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


def test_classify_bracket_recognizes_one_through_hole_and_facing_faces():
    """Кронштейн.STEP — 1 сквозное отверстие Ø25, деталь поддерживается
    (is_supported=True) несмотря на 17 нераспознанных граней (галтели +
    фаски) из 20 — фаски/скругления на кромках не блокируют поддержку
    призматической детали (см. модуль docstring topology_feature_classifier.py)."""
    python_path = _require_pythonocc()
    step_path = _require(BRACKET_STEP)

    topology = extract_step_topology(step_path, python_path)
    features = classify_topology(topology)

    assert features.is_supported is True
    assert len(features.holes) == 1
    hole = features.holes[0]
    assert hole.diameter_mm == pytest.approx(25.0, abs=0.1)
    assert hole.through is True
    assert len(features.millable_faces) >= 1
    assert features.total_face_count == 20


def test_classify_shaft_is_rejected_as_revolved_body():
    """Регрессия: без явного отделения тел вращения ступени вала
    (радиусы 22.5-32.5мм при поперечном габарите 65мм) ошибочно
    классифицировались как 9 отверстий — пользователь указал явно: "вал
    делается не фрезерованием, а точением", это не деталь v1 генератора
    фрезерных тулпасов, а не геометрия с неудачно подобранным порогом
    размера."""
    python_path = _require_pythonocc()
    step_path = _require(VAL_STEP)

    topology = extract_step_topology(step_path, python_path)
    features = classify_topology(topology)

    assert features.is_supported is False
    assert len(features.holes) == 0
    assert len(features.millable_faces) == 0


def test_classify_gear_recognizes_center_hole_without_treating_teeth_as_holes():
    python_path = _require_pythonocc()
    step_path = _require(GEAR_STEP)

    topology = extract_step_topology(step_path, python_path)
    features = classify_topology(topology)

    assert features.is_supported is True
    assert len(features.holes) == 1


def test_classify_synthetic_plate_with_no_features_is_still_supported_via_facing():
    """Синтетическая топология (без внешнего pythonocc) — плита без
    отверстий, только верхняя и нижняя грани перпендикулярны Z. Деталь
    всё равно is_supported=True, потому что facing (обработка граней) —
    самостоятельная поддерживаемая фича, не требует отверстий."""
    topology = PartTopology(
        planar_faces=(
            PlanarFace(origin_mm=(0, 0, 20), normal=(0, 0, 1), extent_u_mm=100, extent_v_mm=100),
            PlanarFace(origin_mm=(0, 0, 0), normal=(0, 0, -1), extent_u_mm=100, extent_v_mm=100),
        ),
        cylindrical_faces=(),
        other_face_count=0,
        total_face_count=2,
        bounding_box_mm=(0, 100, 0, 100, 0, 20),
    )

    features = classify_topology(topology)

    assert features.is_supported is True
    assert len(features.millable_faces) == 2
    assert len(features.holes) == 0


def test_classify_synthetic_sphere_only_shape_is_unsupported():
    """Деталь без единой плоской грани по Z и без цилиндров вообще —
    ничего не распознано, is_supported=False, не мусорная генерация."""
    topology = PartTopology(
        planar_faces=(),
        cylindrical_faces=(),
        other_face_count=6,
        total_face_count=6,
        bounding_box_mm=(0, 50, 0, 50, 0, 50),
    )

    features = classify_topology(topology)

    assert features.is_supported is False
    assert features.unrecognized_face_count == 6


def test_classify_synthetic_revolved_body_with_few_coaxial_cylinders_is_not_falsely_rejected():
    """Деталь с ровно 2 соосными полнооборотными цилиндрами (напр.
    втулка с одним отверстием и одной внешней ступенью) не должна
    ложно попадать под критерий "тело вращения" — порог требует минимум
    3 соосных полнооборотных цилиндра (см. _REVOLVED_BODY_MIN_COAXIAL_COUNT)."""
    topology = PartTopology(
        planar_faces=(
            PlanarFace(origin_mm=(0, 0, 20), normal=(0, 0, 1), extent_u_mm=10, extent_v_mm=10),
        ),
        cylindrical_faces=(
            CylindricalFace(
                radius_mm=5,
                axis_origin_mm=(0, 0, 0),
                axis_direction=(0, 0, 1),
                angular_extent_rad=6.283,
                is_full_turn=True,
                height_mm=18,
            ),
            CylindricalFace(
                radius_mm=15,
                axis_origin_mm=(0, 0, 0),
                axis_direction=(0, 0, 1),
                angular_extent_rad=6.283,
                is_full_turn=True,
                height_mm=20,
            ),
        ),
        other_face_count=0,
        total_face_count=3,
        bounding_box_mm=(-15, 15, -15, 15, 0, 20),
    )

    features = classify_topology(topology)

    assert features.is_supported is True

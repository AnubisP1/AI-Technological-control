from pathlib import Path

import pytest

from app.domain.cad.feature_model import MillableFace, PartFeatureSet, RecognizedHole
from app.infrastructure.cad.step_feature_extractor import extract_step_topology
from app.infrastructure.config import get_settings
from app.infrastructure.db.sqlite_process_planning_lookup import SqliteProcessPlanningLookup
from app.services.toolpath_generator_service import ToolpathGeneratorService
from app.services.topology_feature_classifier import classify_topology

LITERATURE_ROOT = Path(__file__).resolve().parents[3] / "Литература" / "НПО 2026"
BRACKET_STEP = LITERATURE_ROOT / "Кронштейн" / "Кронштейн.STEP"

_ALUM_MATERIAL_GROUP_ID = 5
_STEEL_CARBON_MATERIAL_GROUP_ID = 1


def _require(path: Path) -> Path:
    if not path.exists():
        pytest.skip(f"fixture недоступен в этом окружении: {path}")
    return path


def _require_pythonocc() -> Path:
    python_path = get_settings().pythonocc_python_path
    if python_path is None or not python_path.exists():
        pytest.skip("PYTHONOCC_PYTHON_PATH не настроен в этом окружении — извлечение топологии недоступно")
    return python_path


def _real_lookup() -> SqliteProcessPlanningLookup:
    db_path = Path(__file__).resolve().parents[1] / "data" / "metal.sqlite"
    if not db_path.exists():
        pytest.skip("data/metal.sqlite отсутствует в этом окружении")
    return SqliteProcessPlanningLookup(db_path)


def test_generate_toolpath_for_real_bracket_fixture_produces_facing_and_hole_operations():
    """Сквозной тест на реальной геометрии: Кронштейн.STEP -> топология ->
    классификация фич -> тулпас. Проверяет, что каждая операция несёт
    реально вычисленные (не константные) обороты/подачу/G-code."""
    python_path = _require_pythonocc()
    step_path = _require(BRACKET_STEP)

    topology = extract_step_topology(step_path, python_path)
    features = classify_topology(topology)
    lookup = _real_lookup()
    generator = ToolpathGeneratorService(lookup)

    plan = generator.generate(
        part_name="Кронштейн",
        feature_set=features,
        material_group_id=_ALUM_MATERIAL_GROUP_ID,
        bounding_box_mm=topology.bounding_box_mm,
    )

    assert plan.unsupported_warning is None
    assert len(plan.operations) >= 2  # facing верхней грани + отверстие

    feature_kinds = {op.feature_kind for op in plan.operations}
    assert "facing" in feature_kinds
    assert "hole" in feature_kinds

    for op in plan.operations:
        assert op.spindle_speed_rpm > 0
        assert op.feed_mm_min > 0
        assert op.tool_diameter_mm > 0
        assert len(op.moves) > 0
        assert len(op.gcode_lines) > 0
        assert op.estimated_time_min > 0
        assert op.source_note != ""
        # G-code содержит реальные координаты, не placeholder-текст.
        assert any(line.startswith("G0") or line.startswith("G1") for line in op.gcode_lines)

    hole_op = next(op for op in plan.operations if op.feature_kind == "hole")
    # НСИ содержит только сверло Ø10 — отверстие Ø25 не может сверлиться
    # им напрямую, генератор обязан честно переключиться на круговую
    # интерполяцию концевой фрезой и явно это отметить, не молчать.
    assert "круговой интерполяцией" in hole_op.source_note


def test_generate_toolpath_returns_unsupported_warning_for_unsupported_feature_set():
    lookup = _real_lookup()
    generator = ToolpathGeneratorService(lookup)

    unsupported_features = PartFeatureSet(is_supported=False, total_face_count=39, unrecognized_face_count=39)

    plan = generator.generate(
        part_name="Вал",
        feature_set=unsupported_features,
        material_group_id=_STEEL_CARBON_MATERIAL_GROUP_ID,
        bounding_box_mm=(0, 707, -32.5, 32.5, -32.5, 32.5),
    )

    assert plan.unsupported_warning is not None
    assert plan.operations == ()


def test_generate_toolpath_warns_but_does_not_crash_when_material_has_no_feed_reference():
    """Материал без засеянных feed_reference (напр. группа STEEL_TOOL —
    инструментальная сталь, для неё нет данных подачи фрезерования в
    НСИ) — сервис обязан вернуть план с предупреждением по операции, не
    выдумать число и не упасть."""
    lookup = _real_lookup()
    generator = ToolpathGeneratorService(lookup)

    features = PartFeatureSet(
        millable_faces=(MillableFace(z_height_mm=20.0, normal_up=True),),
        holes=(),
        is_supported=True,
        total_face_count=1,
    )

    steel_tool_group_id = 6  # STEEL_TOOL — нет засеянных feed_reference для MILL
    plan = generator.generate(
        part_name="Синтетическая плита",
        feature_set=features,
        material_group_id=steel_tool_group_id,
        bounding_box_mm=(0, 100, 0, 100, 0, 20),
    )

    assert plan.unsupported_warning is None
    assert plan.operations == ()
    assert len(plan.warnings) >= 1
    assert "MILL" in plan.warnings[0]


def test_generate_toolpath_recognizes_hole_via_exact_drill_match_when_available():
    """Когда в НСИ есть сверло точного диаметра — используется сверление,
    а не круговая интерполяция (проверка на синтетической фиче с
    диаметром отверстия, совпадающим с засеянным сверлом Ø10)."""
    lookup = _real_lookup()
    generator = ToolpathGeneratorService(lookup)

    features = PartFeatureSet(
        millable_faces=(),
        holes=(RecognizedHole(center_xy_mm=(0, 0), diameter_mm=10.0, depth_mm=15.0, through=False),),
        is_supported=True,
        total_face_count=1,
    )

    plan = generator.generate(
        part_name="Синтетическая деталь с отверстием Ø10",
        feature_set=features,
        material_group_id=_STEEL_CARBON_MATERIAL_GROUP_ID,
        bounding_box_mm=(-20, 20, -20, 20, 0, 20),
    )

    assert len(plan.operations) == 1
    hole_op = plan.operations[0]
    assert hole_op.feature_kind == "hole"
    assert hole_op.tool_diameter_mm == pytest.approx(10.0)
    assert "круговой интерполяцией" not in hole_op.source_note

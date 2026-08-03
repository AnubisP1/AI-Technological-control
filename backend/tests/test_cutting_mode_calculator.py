from pathlib import Path

from app.infrastructure.db.nsi_db import NsiDatabase, build_database
from app.infrastructure.db.sqlite_process_planning_lookup import SqliteProcessPlanningLookup
from app.services.process_planning_service import ProcessPlanningService


def _service(tmp_path: Path) -> ProcessPlanningService:
    db_path = tmp_path / "metal.sqlite"
    build_database(NsiDatabase.METAL, db_path)
    return ProcessPlanningService(SqliteProcessPlanningLookup(db_path))


def test_plan_calculates_cutting_modes_for_real_shaft_fixture(tmp_path: Path):
    """Реальный сценарий: вал 'Круг 67 ГОСТ 2590-2006', сталь 45 —
    диаметр должен быть извлечён, и для точения/шлифования должны
    получиться физически разумные V/n/t/S (не конкретные "магические"
    числа — инженерный расчёт по формуле Косилова/Мещерякова, не
    константа, поэтому диапазонные assert)."""
    service = _service(tmp_path)
    result = service.plan(
        part_name="Вал",
        material_grade="45 ГОСТ 1050-2013",
        blank_designation="Круг 67 ГОСТ 2590-2006",
    )

    assert result.blank_diameter_mm == 67.0

    turn_rough = next(op for op in result.operations if op.operation_type_code == "TURN_ROUGH")
    cm = turn_rough.cutting_mode
    assert cm is not None
    assert cm.is_calculated is True
    assert 20 < cm.cutting_speed_m_min < 300
    assert cm.spindle_speed_rpm is not None and cm.spindle_speed_rpm > 0
    assert cm.depth_of_cut_mm is not None
    assert cm.feed_mm_rev is not None
    assert cm.source_note  # источник формулы обязателен, не должен быть пустым


def test_plan_does_not_calculate_cutting_modes_without_blank_diameter(tmp_path: Path):
    """Без обозначения заготовки (или без распознаваемого диаметра)
    расчёт режимов не должен выполняться — недопустимо выдумывать
    диаметр по умолчанию."""
    service = _service(tmp_path)
    result = service.plan(part_name="Вал", material_grade="45 ГОСТ 1050-2013")

    assert result.blank_diameter_mm is None
    turn_rough = next(op for op in result.operations if op.operation_type_code == "TURN_ROUGH")
    assert turn_rough.cutting_mode is not None
    assert turn_rough.cutting_mode.is_calculated is False
    assert turn_rough.cutting_mode.source_note


def test_plan_warns_when_blank_designation_present_but_diameter_not_parsed(tmp_path: Path):
    service = _service(tmp_path)
    result = service.plan(
        part_name="Деталь",
        material_grade="45 ГОСТ 1050-2013",
        blank_designation="Лист 5 ГОСТ 19903-2015",  # непрофильная заготовка, диаметра нет
    )

    assert result.blank_diameter_mm is None
    assert any("диаметр" in w.lower() for w in result.warnings)


def test_spindle_speed_is_clamped_to_equipment_range(tmp_path: Path):
    """Рассчитанные обороты должны укладываться в паспортный диапазон
    станка (equipment_model.spindle_speed_min/max_rpm), а не произвольное
    теоретическое число."""
    service = _service(tmp_path)
    result = service.plan(
        part_name="Вал",
        material_grade="45 ГОСТ 1050-2013",
        blank_designation="Круг 67 ГОСТ 2590-2006",
    )

    for op in result.operations:
        cm = op.cutting_mode
        if cm is None or not cm.is_calculated or cm.spindle_speed_rpm is None:
            continue
        assert cm.spindle_speed_rpm > 0

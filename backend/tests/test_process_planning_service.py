from pathlib import Path

from app.infrastructure.db.nsi_db import NsiDatabase, build_database
from app.infrastructure.db.sqlite_process_planning_lookup import SqliteProcessPlanningLookup
from app.services.process_planning_service import ProcessPlanningService


def _service(tmp_path: Path) -> ProcessPlanningService:
    db_path = tmp_path / "metal.sqlite"
    build_database(NsiDatabase.METAL, db_path)
    return ProcessPlanningService(SqliteProcessPlanningLookup(db_path))


def test_plan_finds_turning_and_grinding_operations_for_steel_45(tmp_path: Path):
    """Реальный случай из fixture 1 (вал, материал '45 ГОСТ 1050-2013') —
    прокат сортовой + сталь конструкционная должны дать токарные и
    шлифовальную операции согласно правилам совместимости demo-НСИ."""
    service = _service(tmp_path)
    result = service.plan(part_name="Вал", material_grade="45 ГОСТ 1050-2013")

    assert result.material_grade == "45 ГОСТ 1050-2013"
    assert result.workpiece_type_name == "ROLLED_BAR"
    codes = [op.operation_type_code for op in result.operations]
    assert "TURN_ROUGH" in codes
    assert "TURN_FIN" in codes
    assert "GRIND" in codes
    # Порядок операций технологически осмыслен: черновая перед чистовой.
    assert codes.index("TURN_ROUGH") < codes.index("TURN_FIN")


def test_plan_assigns_equipment_model_and_tooling_to_each_operation(tmp_path: Path):
    service = _service(tmp_path)
    result = service.plan(part_name="Вал", material_grade="45 ГОСТ 1050-2013")

    turn_rough = next(op for op in result.operations if op.operation_type_code == "TURN_ROUGH")
    assert turn_rough.equipment_model_name == "16К20"
    assert len(turn_rough.tooling_names) > 0


def test_plan_excludes_drill_operation_when_not_compatible_with_rolled_bar(tmp_path: Path):
    """Демонстрационная НСИ связывает сверлильный станок только с
    поковкой/отливкой (workpiece_type_id 3/4), не с прокатом сортовым —
    сервис не должен выдумывать сверлильную операцию, которой правило
    совместимости не разрешает."""
    service = _service(tmp_path)
    result = service.plan(part_name="Вал", material_grade="45 ГОСТ 1050-2013")

    codes = [op.operation_type_code for op in result.operations]
    assert "DRILL" not in codes


def test_plan_returns_warning_when_material_not_recognized(tmp_path: Path):
    service = _service(tmp_path)
    result = service.plan(part_name="Деталь", material_grade=None)

    assert result.is_empty
    assert len(result.warnings) == 1
    assert "не распознан" in result.warnings[0]


def test_plan_returns_warning_when_material_not_in_nsi(tmp_path: Path):
    service = _service(tmp_path)
    result = service.plan(part_name="Деталь", material_grade="Титан ВТ6 ГОСТ 19807-91")

    assert result.is_empty
    assert len(result.warnings) == 1
    assert "не найден в справочнике" in result.warnings[0]


def test_plan_includes_typical_technical_requirements_from_ost_1_02504_84(tmp_path: Path):
    """Сталь 45 (STEEL_CARBON) должна получить и общие пункты табл. 11
    (не привязанные к operation_type_id), и пункты табл. 16 упрочнения,
    применимые к сталям — см. seed_typical_technical_requirements.sql."""
    service = _service(tmp_path)
    result = service.plan(part_name="Вал", material_grade="45 ГОСТ 1050-2013")

    codes_text = " ".join(req.text for req in result.technical_requirements)
    assert "Неуказанные предельные отклонения размеров" in codes_text
    assert "Виброшлифование" in codes_text
    assert any(req.reference_standard == "ОСТ 1 00022-80" for req in result.technical_requirements)


def test_plan_excludes_aluminum_only_hardening_methods_for_steel(tmp_path: Path):
    service = _service(tmp_path)
    result = service.plan(part_name="Вал", material_grade="45 ГОСТ 1050-2013")

    method_names = [req.text for req in result.technical_requirements]
    assert not any("Дробеструйный метод" in text for text in method_names)

from pathlib import Path

from app.infrastructure.db.nsi_db import NsiDatabase, build_database
from app.infrastructure.db.sqlite_print_planning_lookup import SqlitePrintPlanningLookup
from app.services.print_process_planning_service import PrintProcessPlanningService


def _service(tmp_path: Path) -> PrintProcessPlanningService:
    db_path = tmp_path / "additive.sqlite"
    build_database(NsiDatabase.ADDITIVE, db_path)
    return PrintProcessPlanningService(SqlitePrintPlanningLookup(db_path))


def test_plan_fdm_petg_finds_printer_and_optional_postprocessing(tmp_path: Path):
    service = _service(tmp_path)
    result = service.plan(
        part_name="Корпус датчика", am_technology_code="FDM", material_group_code="PETG"
    )

    assert result.am_material_group_name == "PETG"
    assert result.printer_model_name is not None
    assert not result.is_empty
    # Филаменты в demo-НСИ имеют опциональную (не обязательную) постобработку.
    assert all(not step.is_required for step in result.postprocessing_steps)


def test_plan_sla_resin_requires_wash_then_cure_in_order(tmp_path: Path):
    """SLA-смола в demo-НСИ обязательно требует мойку -> дозасветку в этом
    порядке (typical_order 1 -> 2) — критичное отличие печати от
    механообработки, где постобработка обычно опциональна."""
    service = _service(tmp_path)
    result = service.plan(
        part_name="Крышка", am_technology_code="SLA", material_group_code="RESIN_STD"
    )

    assert result.printer_model_name == "Formlabs Form 3"
    assert len(result.postprocessing_steps) == 2
    assert all(step.is_required for step in result.postprocessing_steps)
    names = [step.pp_tooling_type_name for step in result.postprocessing_steps]
    assert "Мойка" in names[0]
    assert "дозасветки" in names[1]


def test_plan_returns_warning_when_technology_unknown(tmp_path: Path):
    service = _service(tmp_path)
    result = service.plan(part_name="Деталь", am_technology_code="FUSED_GLASS", material_group_code="X")

    assert result.is_empty
    assert len(result.warnings) == 1
    assert "не найдена" in result.warnings[0]


def test_plan_returns_warning_when_material_not_in_nsi_for_technology(tmp_path: Path):
    """PLA относится к FDM, а не к SLA — запрос комбинации из разных
    технологий должен явно провалиться, а не тихо подобрать что-то не то."""
    service = _service(tmp_path)
    result = service.plan(part_name="Деталь", am_technology_code="SLA", material_group_code="PLA")

    assert result.is_empty
    assert len(result.warnings) == 1
    assert "не найден в справочнике" in result.warnings[0]

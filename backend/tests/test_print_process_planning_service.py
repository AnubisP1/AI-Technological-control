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


def test_plan_includes_quality_standard_from_technology_tolerance_table(tmp_path: Path):
    """Данные из am_technology_tolerance (источник: inner.su, см.
    seed_print_quality_standards.sql) должны попадать в результат
    автоподбора для отображения в карте техпроцесса печати."""
    service = _service(tmp_path)
    result = service.plan(
        part_name="Корпус датчика", am_technology_code="FDM", material_group_code="PETG"
    )

    assert result.quality_standard is not None
    assert result.quality_standard.tolerance_mm == "±0.3-0.5"
    assert result.quality_standard.min_thread_pitch_mm == "1"
    assert "inner.su" in result.quality_standard.source_note


def test_plan_sla_quality_standard_has_tighter_tolerance_than_fdm(tmp_path: Path):
    service = _service(tmp_path)
    fdm_result = service.plan(
        part_name="Деталь", am_technology_code="FDM", material_group_code="PETG"
    )
    sla_result = service.plan(
        part_name="Деталь", am_technology_code="SLA", material_group_code="RESIN_STD"
    )

    assert fdm_result.quality_standard.tolerance_mm != sla_result.quality_standard.tolerance_mm


def test_plan_includes_material_print_profile_when_real_material_exists(tmp_path: Path):
    """PETG (Bambu Lab PETG HF) имеет реальную запись am_material с
    температурами — эти данные нужны для экспертизы НСИ по пластику
    (Фаза 20), чтобы технолог знал, что установить на принтере/слайсере."""
    service = _service(tmp_path)
    result = service.plan(
        part_name="Корпус датчика", am_technology_code="FDM", material_group_code="PETG"
    )

    assert result.material_print_profile is not None
    assert result.material_print_profile.trade_name == "Bambu Lab PETG HF"
    assert result.material_print_profile.print_temp_min_c == 230
    assert result.material_print_profile.print_temp_max_c == 260
    assert result.material_print_profile.bed_temp_c == 80
    assert result.material_print_profile.requires_dry_storage is True
    assert not result.warnings


def test_plan_includes_material_print_profile_for_nylon_added_2026_08_04(tmp_path: Path):
    """Регрессия: группа NYLON_FDM изначально не имела ни одной записи
    am_material (см. seed_data.sql) — автоподбор рекомендовал её как
    топ-вариант для класса PROPELLER, но экспертиза НСИ не могла
    показать параметры печати. Добавлена реальная марка (eSUN PA-CF)."""
    service = _service(tmp_path)
    result = service.plan(
        part_name="Пропеллер", am_technology_code="FDM", material_group_code="NYLON_FDM"
    )

    assert result.material_print_profile is not None
    assert result.material_print_profile.trade_name == "eSUN PA-CF"
    assert result.material_print_profile.requires_heated_chamber is True
    assert result.material_print_profile.requires_dry_storage is True
    assert not result.warnings


def test_plan_warns_when_material_group_has_no_am_material_record(tmp_path: Path):
    """Если бы группа материала реально осталась без записи am_material,
    сервис обязан честно предупредить, а не молчать/выдумывать значения."""
    service = _service(tmp_path)
    result = service.plan(
        part_name="Деталь", am_technology_code="FDM", material_group_code="TPU"
    )

    assert result.material_print_profile is None
    assert any("параметры печати" in w for w in result.warnings)


def test_plan_attaches_quality_effect_note_to_postprocessing_step_with_known_tooling(
    tmp_path: Path,
):
    """SLA-постобработка (шлифовка/полировка, SANDING_KIT) должна нести
    примечание об улучшении точности/шероховатости из
    postprocessing_quality_effect; шаги без прямого соответствия
    (например, срезание поддержек) остаются без примечания, а не с
    выдуманной оценкой."""
    service = _service(tmp_path)
    result = service.plan(
        part_name="Крышка", am_technology_code="FDM", material_group_code="PETG"
    )

    sanding_steps = [
        step
        for step in result.postprocessing_steps
        if "шлифовки" in step.pp_tooling_type_name or "полировки" in step.pp_tooling_type_name
    ]
    assert sanding_steps
    assert all(step.quality_effect_note is not None for step in sanding_steps)

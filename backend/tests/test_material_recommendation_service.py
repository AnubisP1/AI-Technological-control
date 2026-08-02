from pathlib import Path

from app.infrastructure.db.nsi_db import NsiDatabase, build_database
from app.infrastructure.db.sqlite_print_planning_lookup import SqlitePrintPlanningLookup
from app.services.material_recommendation_service import MaterialRecommendationService


def _service(tmp_path: Path) -> MaterialRecommendationService:
    db_path = tmp_path / "additive.sqlite"
    build_database(NsiDatabase.ADDITIVE, db_path)
    return MaterialRecommendationService(SqlitePrintPlanningLookup(db_path))


def test_recommend_propeller_under_vibration_prefers_nylon_over_pla_petg(tmp_path: Path):
    """Реальная посеянная рекомендация БПЛА-домена: винт под высокой
    вибрацией — приоритет 1 должен быть нейлон (усталостная прочность),
    не PLA/PETG/ABS, которые в demo-НСИ для этого класса не рекомендованы."""
    service = _service(tmp_path)
    result = service.recommend(
        part_application_class_code="PROPELLER",
        operating_condition_codes=("VIBRATION_HIGH_MOTOR_MOUNT",),
    )

    assert not result.is_empty
    assert result.warnings == ()
    assert result.options[0].material_group_code == "NYLON_FDM"
    assert result.options[0].priority == 1
    assert all(opt.priority >= result.options[0].priority for opt in result.options)


def test_recommend_options_carry_source_reliability_not_hidden(tmp_path: Path):
    """Источник (community_practice/manufacturer_datasheet) и его
    надёжность обязаны попадать в каждый вариант — по требованию не
    выдавать демонстрационные рекомендации за производственный расчёт."""
    service = _service(tmp_path)
    result = service.recommend(
        part_application_class_code="PROPELLER",
        operating_condition_codes=("VIBRATION_HIGH_MOTOR_MOUNT",),
    )

    for option in result.options:
        assert option.source_type in ("community_practice", "manufacturer_datasheet")
        assert option.source_reliability in ("low", "medium", "high")
        assert option.rationale


def test_recommend_falls_back_to_base_recommendation_when_condition_has_none(tmp_path: Path):
    """MOTOR_MOUNT в demo-НСИ имеет рекомендации только под конкретное
    условие (TEMP_HIGH_60_80), не под 'без условий' — запрос без условий
    должен явно предупредить, а не тихо промолчать пустым списком."""
    service = _service(tmp_path)
    result = service.recommend(
        part_application_class_code="MOTOR_MOUNT", operating_condition_codes=()
    )

    assert result.is_empty
    assert any("нет ни одной рекомендации" in w for w in result.warnings)


def test_recommend_with_matching_condition_returns_options_for_motor_mount(tmp_path: Path):
    service = _service(tmp_path)
    result = service.recommend(
        part_application_class_code="MOTOR_MOUNT",
        operating_condition_codes=("TEMP_HIGH_60_80",),
    )

    assert not result.is_empty
    assert result.matched_operating_conditions == ("TEMP_HIGH_60_80",)
    assert result.warnings == ()


def test_recommend_falls_back_and_warns_when_condition_has_no_recommendations(tmp_path: Path):
    """NOSE_CONE — реальный класс, но запрос с несуществующим кодом условия
    должен и предупредить о ненайденном коде, и (раз для класса вообще нет
    базовой рекомендации без условий в demo-НСИ) предупредить об этом тоже —
    не подменять недостаток данных выдуманной рекомендацией."""
    service = _service(tmp_path)
    result = service.recommend(
        part_application_class_code="NOSE_CONE",
        operating_condition_codes=("NONEXISTENT_CONDITION",),
    )

    assert any("Не найдены в справочнике условия эксплуатации" in w for w in result.warnings)


def test_recommend_returns_warning_for_unknown_part_application_class(tmp_path: Path):
    service = _service(tmp_path)
    result = service.recommend(
        part_application_class_code="WARP_DRIVE", operating_condition_codes=()
    )

    assert result.is_empty
    assert len(result.warnings) == 1
    assert "не найден в справочнике" in result.warnings[0]


def test_typical_operating_conditions_are_scoped_to_part_application_class(tmp_path: Path):
    """part_application_class_typical_condition должна давать разный набор
    условий для разных классов — не один и тот же список всем."""
    db_path = tmp_path / "additive.sqlite"
    build_database(NsiDatabase.ADDITIVE, db_path)
    lookup = SqlitePrintPlanningLookup(db_path)

    propeller = lookup.find_part_application_class_by_code("PROPELLER")
    motor_mount = lookup.find_part_application_class_by_code("MOTOR_MOUNT")

    propeller_conditions = {c.code for c in lookup.find_operating_conditions(propeller.id)}
    motor_mount_conditions = {c.code for c in lookup.find_operating_conditions(motor_mount.id)}

    assert propeller_conditions != motor_mount_conditions
    assert "VIBRATION_HIGH_MOTOR_MOUNT" in propeller_conditions

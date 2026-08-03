from pathlib import Path

from app.domain.cad.step_model import BoundingBox
from app.infrastructure.db.nsi_db import NsiDatabase, build_database
from app.infrastructure.db.sqlite_print_planning_lookup import SqlitePrintPlanningLookup
from app.services.print_process_planning_service import PrintProcessPlanningService

_REAL_SQUID_LID_BBOX = BoundingBox(
    x_min=0, x_max=109.053, y_min=0, y_max=98.383, z_min=0, z_max=196.766
)


def _service(tmp_path: Path) -> PrintProcessPlanningService:
    db_path = tmp_path / "additive.sqlite"
    build_database(NsiDatabase.ADDITIVE, db_path)
    return PrintProcessPlanningService(SqlitePrintPlanningLookup(db_path))


def test_plan_calculates_print_estimate_with_real_bounding_box(tmp_path: Path):
    """Реальный fixture (крышка SQUID RUS 2, FDM/PETG) — оценка должна
    быть рассчитана и физически правдоподобна (не выдуманное число:
    положительное время печати и масса, с явным source_note)."""
    service = _service(tmp_path)
    result = service.plan(
        part_name="Крышка SQUID RUS 2",
        am_technology_code="FDM",
        material_group_code="PETG",
        bounding_box=_REAL_SQUID_LID_BBOX,
    )

    estimate = result.print_estimate
    assert estimate is not None
    assert estimate.layer_height_mm > 0
    assert estimate.estimated_print_time_min > 0
    assert estimate.estimated_material_g > 0
    assert estimate.source_note  # источник оценки обязателен


def test_plan_does_not_calculate_print_estimate_without_bounding_box(tmp_path: Path):
    """Без геометрии (bounding_box=None) оценка не должна выполняться —
    недопустимо выдумывать время печати/расход без размеров детали."""
    service = _service(tmp_path)
    result = service.plan(
        part_name="Крышка SQUID RUS 2",
        am_technology_code="FDM",
        material_group_code="PETG",
        bounding_box=None,
    )

    assert result.print_estimate is None


def test_print_estimate_scales_with_volume(tmp_path: Path):
    """Более крупная деталь того же материала/технологии должна дать
    большую расчётную массу и время печати — простая проверка, что
    расчёт действительно реагирует на геометрию, а не на константу."""
    service = _service(tmp_path)
    small = service.plan(
        part_name="Малая деталь",
        am_technology_code="FDM",
        material_group_code="PETG",
        bounding_box=BoundingBox(x_min=0, x_max=10, y_min=0, y_max=10, z_min=0, z_max=10),
    )
    large = service.plan(
        part_name="Крупная деталь",
        am_technology_code="FDM",
        material_group_code="PETG",
        bounding_box=BoundingBox(x_min=0, x_max=100, y_min=0, y_max=100, z_min=0, z_max=100),
    )

    assert large.print_estimate.estimated_material_g > small.print_estimate.estimated_material_g
    assert large.print_estimate.estimated_print_time_min > small.print_estimate.estimated_print_time_min

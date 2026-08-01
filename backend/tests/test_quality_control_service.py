from pathlib import Path

from app.domain.manufacturing.simulation_model import SimulatedOperation, SimulationPlan
from app.domain.quality_control.photo_comparator_port import IPhotoComparator
from app.domain.quality_control.quality_model import PhotoComparisonResult, QualityVerdict
from app.services.quality_control_service import QualityControlService


class _StubComparator(IPhotoComparator):
    def __init__(self, result: PhotoComparisonResult) -> None:
        self._result = result

    def compare(self, reference_path: Path, actual_path: Path) -> PhotoComparisonResult:
        return self._result


def _metal_plan(operation_count: int) -> SimulationPlan:
    operations = tuple(
        SimulatedOperation(
            sequence_no=i,
            name=f"Операция {i}",
            machine_icon="mill",
            machine_label="станок",
            program_lines=(),
        )
        for i in range(operation_count)
    )
    return SimulationPlan(part_name="Деталь", material_kind="metal", operations=operations)


def test_ok_verdict_generates_serial_production_plan_and_suggestions():
    comparator = _StubComparator(
        PhotoComparisonResult(verdict=QualityVerdict.OK, similarity_score=0.95, notes=("ок",))
    )
    service = QualityControlService(comparator)

    report = service.assess(
        reference_photo_path=Path("ref.jpg"),
        actual_photo_path=Path("actual.jpg"),
        simulation_plan=_metal_plan(4),
        planning_warnings=(),
    )

    assert report.verdict == "ok"
    assert report.serial_production_plan is not None
    assert report.serial_production_plan.operation_count == 4
    assert report.serial_production_plan.risk_level == "low"
    assert report.serial_production_plan.is_demonstration_estimate is True
    assert len(report.optimization_suggestions) > 0
    assert report.remediation_recommendations == ()


def test_ok_verdict_with_warnings_raises_risk_and_defect_rate():
    comparator = _StubComparator(
        PhotoComparisonResult(verdict=QualityVerdict.OK, similarity_score=0.9, notes=())
    )
    service = QualityControlService(comparator)

    report = service.assess(
        reference_photo_path=Path("ref.jpg"),
        actual_photo_path=Path("actual.jpg"),
        simulation_plan=_metal_plan(2),
        planning_warnings=("предупреждение 1", "предупреждение 2"),
    )

    assert report.serial_production_plan.risk_level == "high"
    assert report.serial_production_plan.estimated_defect_rate_percent > 2.0


def test_defective_verdict_generates_remediation_not_serial_plan():
    comparator = _StubComparator(
        PhotoComparisonResult(verdict=QualityVerdict.DEFECTIVE, similarity_score=0.3, notes=("брак",))
    )
    service = QualityControlService(comparator)

    report = service.assess(
        reference_photo_path=Path("ref.jpg"),
        actual_photo_path=Path("actual.jpg"),
        simulation_plan=_metal_plan(3),
    )

    assert report.verdict == "defective"
    assert report.serial_production_plan is None
    assert len(report.remediation_recommendations) > 0
    assert report.optimization_suggestions == ()


def test_inconclusive_verdict_gives_only_report_no_branching():
    comparator = _StubComparator(
        PhotoComparisonResult(verdict=QualityVerdict.INCONCLUSIVE, similarity_score=0.65, notes=("неуверенно",))
    )
    service = QualityControlService(comparator)

    report = service.assess(
        reference_photo_path=Path("ref.jpg"),
        actual_photo_path=Path("actual.jpg"),
        simulation_plan=_metal_plan(3),
    )

    assert report.verdict == "inconclusive"
    assert report.serial_production_plan is None
    assert report.optimization_suggestions == ()
    assert report.remediation_recommendations == ()

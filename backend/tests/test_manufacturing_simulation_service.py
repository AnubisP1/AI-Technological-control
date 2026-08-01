from app.domain.process_planning.print_process_model import (
    PlannedPostprocessingStep,
    PrintProcessPlanningResult,
)
from app.domain.process_planning.process_model import PlannedOperation, ProcessPlanningResult
from app.services.manufacturing_simulation_service import ManufacturingSimulationService


def test_build_metal_plan_maps_operations_to_icons_and_programs():
    result = ProcessPlanningResult(
        part_name="Вал",
        material_grade="Сталь 45",
        workpiece_type_name="ROLLED_BAR",
        operations=(
            PlannedOperation(
                sequence_no=5,
                operation_type_code="TURN_ROUGH",
                operation_type_name="Точение черновое",
                equipment_type_code="LATHE_CNC",
                equipment_model_name="16К20Ф3",
            ),
            PlannedOperation(
                sequence_no=10,
                operation_type_code="CONTROL",
                operation_type_name="Контроль",
                equipment_type_code="CONTROL_STATION",
                equipment_model_name=None,
            ),
        ),
    )

    plan = ManufacturingSimulationService().build_metal_plan(result)

    assert plan.material_kind == "metal"
    assert plan.total_seconds == 15
    assert len(plan.operations) == 2

    turning = plan.operations[0]
    assert turning.machine_icon == "lathe"
    assert turning.machine_label == "16К20Ф3"
    assert turning.program_lines[0] == "%"

    control = plan.operations[1]
    assert control.machine_icon == "control"
    # Контроль — не станочная операция, управляющей программы для неё нет.
    assert control.program_lines == ()


def test_build_metal_plan_empty_when_no_operations():
    result = ProcessPlanningResult(part_name="Деталь", material_grade=None, workpiece_type_name=None)

    plan = ManufacturingSimulationService().build_metal_plan(result)

    assert plan.is_empty
    assert plan.operations == ()


def test_build_print_plan_orders_print_before_postprocessing():
    result = PrintProcessPlanningResult(
        part_name="Крышка",
        am_technology_code="SLA",
        am_material_group_name="RESIN_STD",
        printer_model_name="Formlabs Form 3",
        postprocessing_steps=(
            PlannedPostprocessingStep(sequence_no=1, pp_tooling_type_name="Мойка в IPA", is_required=True),
            PlannedPostprocessingStep(
                sequence_no=2, pp_tooling_type_name="УФ-дозасветка", is_required=True
            ),
        ),
    )

    plan = ManufacturingSimulationService().build_print_plan(result)

    assert plan.material_kind == "plastic"
    assert len(plan.operations) == 3

    printing = plan.operations[0]
    assert printing.machine_icon == "resin_printer"
    assert printing.machine_label == "Formlabs Form 3"
    assert printing.program_lines[0].startswith(";")

    wash, cure = plan.operations[1], plan.operations[2]
    assert wash.name == "Мойка в IPA"
    assert cure.name == "УФ-дозасветка"
    assert wash.program_lines == ()


def test_build_print_plan_empty_when_material_not_found():
    result = PrintProcessPlanningResult(
        part_name="Деталь",
        am_technology_code="FDM",
        am_material_group_name=None,
        printer_model_name=None,
        warnings=("Материал не найден",),
    )

    plan = ManufacturingSimulationService().build_print_plan(result)

    assert plan.is_empty

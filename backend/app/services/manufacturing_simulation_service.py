"""Сервис симуляции изготовления (Модуль 2, второй шаг — после
согласования ТД).

Строит SimulationPlan из уже полученного результата автоподбора
техпроцесса (Модуль 1.3) — не выполняет собственный подбор оборудования
повторно. Для металла источник — ProcessPlanningResult (список
PlannedOperation), для пластика — PrintProcessPlanningResult (печать +
шаги постобработки). Управляющая программа для каждой операции берётся
из статичных шаблонов (infrastructure/manufacturing/program_templates.py)
— это демонстрация построчной генерации в UI, а не расчёт для
конкретной геометрии (см. модуль docstring).
"""

from __future__ import annotations

from app.domain.manufacturing.simulation_model import SimulatedOperation, SimulationPlan
from app.domain.process_planning.print_process_model import PrintProcessPlanningResult
from app.domain.process_planning.process_model import ProcessPlanningResult
from app.infrastructure.manufacturing.program_templates import (
    metal_program_for_operation_type_code,
    print_program_for_printer_type,
)

_METAL_ICON_BY_OPERATION_PREFIX: tuple[tuple[str, str], ...] = (
    ("TURN", "lathe"),
    ("MILL", "mill"),
    ("DRILL", "drill"),
    ("GRIND", "grind"),
    ("CONTROL", "control"),
)

_PRINT_ICON_BY_TECHNOLOGY_PREFIX: tuple[tuple[str, str], ...] = (
    ("FDM", "fdm_printer"),
    ("SLA", "resin_printer"),
    ("MSLA", "resin_printer"),
    ("SLS", "sls_printer"),
)


def _metal_icon_for_operation(operation_type_code: str) -> str:
    upper_code = operation_type_code.upper()
    for prefix, icon in _METAL_ICON_BY_OPERATION_PREFIX:
        if upper_code.startswith(prefix):
            return icon
    return "machine_generic"


def _print_icon_for_technology(am_technology_code: str) -> str:
    upper_code = am_technology_code.upper()
    for prefix, icon in _PRINT_ICON_BY_TECHNOLOGY_PREFIX:
        if upper_code.startswith(prefix):
            return icon
    return "printer_generic"


class ManufacturingSimulationService:
    def build_metal_plan(self, result: ProcessPlanningResult) -> SimulationPlan:
        if result.is_empty:
            return SimulationPlan(part_name=result.part_name, material_kind="metal", operations=())

        operations = tuple(
            SimulatedOperation(
                sequence_no=op.sequence_no,
                name=op.operation_type_name,
                machine_icon=_metal_icon_for_operation(op.operation_type_code),
                machine_label=op.equipment_model_name or op.equipment_type_code,
                program_lines=metal_program_for_operation_type_code(op.operation_type_code),
                duration_share=1.0,
            )
            for op in result.operations
        )
        return SimulationPlan(part_name=result.part_name, material_kind="metal", operations=operations)

    def build_print_plan(self, result: PrintProcessPlanningResult) -> SimulationPlan:
        if result.is_empty:
            return SimulationPlan(part_name=result.part_name, material_kind="plastic", operations=())

        print_step = SimulatedOperation(
            sequence_no=1,
            name=f"Печать ({result.am_technology_code})",
            machine_icon=_print_icon_for_technology(result.am_technology_code),
            machine_label=result.printer_model_name or "модель принтера не определена",
            program_lines=print_program_for_printer_type(result.am_technology_code),
            # Печать — самый долгий этап по сравнению с постобработкой,
            # поэтому ей отдаётся больший вес доли шкалы прогресса.
            duration_share=2.0,
        )

        postprocessing_steps = tuple(
            SimulatedOperation(
                sequence_no=step.sequence_no + 1,
                name=step.pp_tooling_type_name,
                machine_icon="postprocessing",
                machine_label=step.pp_tooling_type_name,
                program_lines=(),
                duration_share=1.0,
            )
            for step in result.postprocessing_steps
        )

        return SimulationPlan(
            part_name=result.part_name,
            material_kind="plastic",
            operations=(print_step, *postprocessing_steps),
        )

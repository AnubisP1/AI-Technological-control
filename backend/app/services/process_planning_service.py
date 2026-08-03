"""Сервис Модуля 1.3 (упрощённый автоподбор техпроцесса) — по решению
пользователя (2026-08-01, dev/QUESTIONS.md) объём Фазы 4 ограничен
простым правило-ориентированным подбором станка/операций по таблицам
совместимости из БД НСИ (equipment_type_material_group,
equipment_type_workpiece_type, equipment_type_operation_type), без
расчёта режимов резания и без полноценного анализа геометрии детали.
Полноценное технологическое проектирование (выбор конкретных переходов,
припусков, режимов) — вне объёма этой фазы.

Правило определения типа заготовки: если у детали есть отверстие
(из STEP, ADVANCED_FACE/CYLINDRICAL с цветовой аннотацией отверстия —
не реализовано детально на этой фазе) — считаем прокат сортовой (пруток/
круг), это самый частый случай для деталей типа вал/втулка среди
тестовых fixture. Явного распознавания формы (вал/плита/корпус) по
геометрии не реализовано — за отсутствием этого анализа тип заготовки
по умолчанию берётся 'ROLLED_BAR', а не угадывается более сложной
эвристикой, которая давала бы ложное впечатление точности.
"""

from __future__ import annotations

from app.domain.material_text import extract_blank_diameter_mm
from app.domain.process_planning.process_model import (
    PlannedOperation,
    ProcessPlanningResult,
    TechnicalRequirementLine,
)
from app.domain.process_planning.process_planning_lookup_port import IProcessPlanningLookup
from app.services.cutting_mode_calculator import CuttingModeCalculator

_DEFAULT_WORKPIECE_TYPE_CODE = "ROLLED_BAR"

# Порядок операций технологически осмыслен (черновая -> чистовая ->
# сверлильная -> контрольная), а не порядок из БД — таблица
# equipment_type_operation_type не хранит приоритет операций.
_OPERATION_ORDER = ["TURN_ROUGH", "TURN_FIN", "MILL", "DRILL", "GRIND", "CONTROL"]


class ProcessPlanningService:
    def __init__(self, lookup: IProcessPlanningLookup) -> None:
        self._lookup = lookup
        self._cutting_mode_calculator = CuttingModeCalculator(lookup)

    def plan(
        self,
        *,
        part_name: str | None,
        material_grade: str | None,
        blank_designation: str | None = None,
    ) -> ProcessPlanningResult:
        warnings: list[str] = []

        if not material_grade:
            return ProcessPlanningResult(
                part_name=part_name,
                material_grade=None,
                workpiece_type_name=None,
                warnings=(
                    "Материал не распознан — автоподбор станков и операций "
                    "невозможен без данных о материале детали.",
                ),
            )

        material_group_id = self._lookup.find_material_group_id(material_grade)
        if material_group_id is None:
            return ProcessPlanningResult(
                part_name=part_name,
                material_grade=material_grade,
                workpiece_type_name=None,
                warnings=(
                    f"Материал '{material_grade}' не найден в справочнике НСИ — "
                    "автоподбор станков и операций невозможен.",
                ),
            )

        workpiece_type_id = self._lookup.find_workpiece_type_id_by_code(
            _DEFAULT_WORKPIECE_TYPE_CODE
        )
        if workpiece_type_id is None:
            return ProcessPlanningResult(
                part_name=part_name,
                material_grade=material_grade,
                workpiece_type_name=None,
                warnings=(
                    f"Тип заготовки по умолчанию '{_DEFAULT_WORKPIECE_TYPE_CODE}' "
                    "не найден в справочнике классификаторов НСИ.",
                ),
            )

        equipment_types = self._lookup.find_equipment_types_for_material_and_workpiece(
            material_group_id, workpiece_type_id
        )
        if not equipment_types:
            warnings.append(
                f"Не найдено ни одного типа станка, совместимого с материалом "
                f"'{material_grade}' и заготовкой данного вида, — обратная связь: "
                "проверить достаточность парка оборудования либо скорректировать "
                "выбор материала/заготовки на этапе проектирования."
            )
            return ProcessPlanningResult(
                part_name=part_name,
                material_grade=material_grade,
                workpiece_type_name=_DEFAULT_WORKPIECE_TYPE_CODE,
                warnings=tuple(warnings),
            )

        blank_diameter_mm = (
            extract_blank_diameter_mm(blank_designation) if blank_designation else None
        )
        if blank_designation and blank_diameter_mm is None:
            warnings.append(
                f"Обозначение заготовки '{blank_designation}' не содержит диаметра "
                "круглого проката (типично для поковки/отливки, где типоразмер "
                "задаётся иначе, напр. группой контроля по ГОСТ 8479-70) — расчёт "
                "режимов резания по формуле недоступен без диаметра, требуется "
                "уточнение у технолога."
            )

        operations = self._plan_operations(
            equipment_types, warnings, material_group_id, blank_diameter_mm
        )
        technical_requirements = self._collect_technical_requirements(
            operations, material_group_id
        )

        return ProcessPlanningResult(
            part_name=part_name,
            material_grade=material_grade,
            workpiece_type_name=_DEFAULT_WORKPIECE_TYPE_CODE,
            operations=operations,
            warnings=tuple(warnings),
            technical_requirements=technical_requirements,
            blank_diameter_mm=blank_diameter_mm,
        )

    def _collect_technical_requirements(
        self, operations: tuple[PlannedOperation, ...], material_group_id: int
    ) -> tuple[TechnicalRequirementLine, ...]:
        operation_type_ids = tuple(
            {
                self._lookup.find_operation_type_id_by_code(op.operation_type_code)
                for op in operations
            }
            - {None}
        )
        machining_requirements = self._lookup.find_machining_requirements_for_operation_types(
            operation_type_ids
        )
        hardening_methods = self._lookup.find_surface_hardening_methods_for_material_group(
            material_group_id
        )
        lines = [
            TechnicalRequirementLine(
                text=req.formulation_template, reference_standard=req.reference_standard
            )
            for req in machining_requirements
        ]
        lines.extend(
            TechnicalRequirementLine(
                text=f"{method.method_name} ({method.applicable_to}) — {method.reference_instruction}"
                if method.applicable_to
                else f"{method.method_name} — {method.reference_instruction}",
                reference_standard=method.reference_instruction,
            )
            for method in hardening_methods
        )
        return tuple(lines)

    def _plan_operations(
        self,
        equipment_types,
        warnings: list[str],
        material_group_id: int,
        blank_diameter_mm: float | None,
    ) -> tuple[PlannedOperation, ...]:
        available_operation_types_by_equipment = {
            et.id: self._lookup.find_operation_types_for_equipment_type(et.id)
            for et in equipment_types
        }

        code_to_operation_type = {}
        code_to_equipment_type = {}
        for et in equipment_types:
            for ot in available_operation_types_by_equipment[et.id]:
                if ot.code not in code_to_operation_type:
                    code_to_operation_type[ot.code] = ot
                    code_to_equipment_type[ot.code] = et

        planned: list[PlannedOperation] = []
        sequence_no = 5
        for code in _OPERATION_ORDER:
            if code not in code_to_operation_type:
                continue
            operation_type = code_to_operation_type[code]
            equipment_type = code_to_equipment_type[code]

            equipment_model = self._lookup.find_equipment_model_for_type(equipment_type.id)
            if equipment_model is None:
                warnings.append(
                    f"Операция '{operation_type.name}' технически возможна "
                    f"(тип станка '{equipment_type.name}'), но в справочнике "
                    "нет ни одной модели этого типа — обратная связь: "
                    "пополнить парк оборудования либо справочник моделей."
                )

            tooling_types = self._lookup.find_tooling_types_for_operation_type(operation_type.id)

            cutting_mode = self._cutting_mode_calculator.calculate(
                operation_type_id=operation_type.id,
                operation_type_code=operation_type.code,
                material_group_id=material_group_id,
                blank_diameter_mm=blank_diameter_mm,
                spindle_speed_min_rpm=(
                    equipment_model.spindle_speed_min_rpm if equipment_model else None
                ),
                spindle_speed_max_rpm=(
                    equipment_model.spindle_speed_max_rpm if equipment_model else None
                ),
            )

            planned.append(
                PlannedOperation(
                    sequence_no=sequence_no,
                    operation_type_code=operation_type.code,
                    operation_type_name=operation_type.name,
                    equipment_type_code=equipment_type.code,
                    equipment_model_name=(
                        equipment_model.model_name if equipment_model else None
                    ),
                    tooling_names=tuple(t.name for t in tooling_types),
                    cutting_mode=cutting_mode,
                )
            )
            sequence_no += 5

        if not planned:
            warnings.append(
                "Ни одна операция не подобрана — тип станка найден, но для "
                "него не определены допустимые виды операций в справочнике "
                "equipment_type_operation_type."
            )

        return tuple(planned)

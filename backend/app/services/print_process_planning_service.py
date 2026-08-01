"""Сервис Модуля 1.3 для пластиковых изделий (аддитивные технологии).

Отличие от металла (ProcessPlanningService): на вход по ТЗ подаётся
только STEP-модель без чертежа — материал и технология печати не могут
быть извлечены из документа (в STEP нет граф материала/техпроцесса) и
указываются пользователем явно при запросе, а не автоматически
распознаются. Подбор принтера и постобработки — по тем же принципам
упрощённого автоподбора, что и для металла (Фаза 4): правила
совместимости из additive-НСИ, без расчёта параметров печати
(высота слоя, время печати, расход материала).
"""

from __future__ import annotations

from app.domain.process_planning.print_planning_lookup_port import IPrintPlanningLookup
from app.domain.process_planning.print_process_model import (
    PlannedPostprocessingStep,
    PrintProcessPlanningResult,
)


class PrintProcessPlanningService:
    def __init__(self, lookup: IPrintPlanningLookup) -> None:
        self._lookup = lookup

    def plan(
        self, *, part_name: str | None, am_technology_code: str, material_group_code: str
    ) -> PrintProcessPlanningResult:
        am_technology_id = self._lookup.find_am_technology_id_by_code(am_technology_code)
        if am_technology_id is None:
            return PrintProcessPlanningResult(
                part_name=part_name,
                am_technology_code=am_technology_code,
                am_material_group_name=None,
                printer_model_name=None,
                warnings=(
                    f"Технология печати '{am_technology_code}' не найдена в "
                    "справочнике НСИ — автоподбор невозможен.",
                ),
            )

        material_group = self._lookup.find_material_group(am_technology_id, material_group_code)
        if material_group is None:
            return PrintProcessPlanningResult(
                part_name=part_name,
                am_technology_code=am_technology_code,
                am_material_group_name=None,
                printer_model_name=None,
                warnings=(
                    f"Материал '{material_group_code}' не найден в справочнике "
                    f"для технологии '{am_technology_code}' — автоподбор невозможен.",
                ),
            )

        warnings: list[str] = []

        printer_types = self._lookup.find_printer_types_for_material_group(material_group.id)
        printer_model_name = None
        if not printer_types:
            warnings.append(
                f"Не найдено ни одного типа принтера, совместимого с материалом "
                f"'{material_group.name}', — обратная связь: проверить достаточность "
                "парка оборудования либо скорректировать выбор материала."
            )
        else:
            printer_model = self._lookup.find_printer_model_for_type(printer_types[0].id)
            if printer_model is None:
                warnings.append(
                    f"Материал '{material_group.name}' совместим с типом принтера "
                    f"'{printer_types[0].name}', но в справочнике нет ни одной "
                    "модели этого типа — пополнить справочник моделей принтеров."
                )
            else:
                printer_model_name = printer_model.model_name

        pp_steps = self._lookup.find_postprocessing_steps_for_material_group(material_group.id)
        postprocessing = tuple(
            PlannedPostprocessingStep(
                sequence_no=step.typical_order or (index + 1),
                pp_tooling_type_name=step.pp_tooling_type_name,
                is_required=step.is_required,
            )
            for index, step in enumerate(sorted(pp_steps, key=lambda s: s.typical_order or 0))
        )

        return PrintProcessPlanningResult(
            part_name=part_name,
            am_technology_code=am_technology_code,
            am_material_group_name=material_group.name,
            printer_model_name=printer_model_name,
            postprocessing_steps=postprocessing,
            warnings=tuple(warnings),
        )

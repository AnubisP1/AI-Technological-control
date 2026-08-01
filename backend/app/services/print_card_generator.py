"""Генератор карты техпроцесса печати и карты постобработки (Модуль 1.3,
пластик) из результата автоподбора (PrintProcessPlanningResult) и
шаблонов am_document_template.

Как и для маршрутной карты металла: графы, которые автоподбор не
рассчитывает (высота слоя, время печати, расход материала, длительность
и температура постобработки), остаются пустыми — не заполняются
выдуманными значениями, т.к. расчёт параметров печати вне объёма
упрощённого автоподбора (Фаза 4).
"""

from __future__ import annotations

from app.domain.process_planning.print_card_model import (
    PostprocessingCard,
    PrintCardRow,
    PrintProcessCard,
)
from app.domain.process_planning.print_process_model import PrintProcessPlanningResult

_NOT_CALCULATED = ""


class PrintCardGenerator:
    def generate_process_card(
        self, planning_result: PrintProcessPlanningResult, *, columns: tuple[str, ...]
    ) -> PrintProcessCard:
        # columns: ["Технология", "Принтер", "Материал", "Высота слоя",
        #           "Заполнение", "Время печати", "Расход материала"]
        row = PrintCardRow(
            values=(
                planning_result.am_technology_code,
                planning_result.printer_model_name or "не подобран",
                planning_result.am_material_group_name or "не определён",
                _NOT_CALCULATED,  # высота слоя — не рассчитывается автоподбором
                _NOT_CALCULATED,  # заполнение
                _NOT_CALCULATED,  # время печати
                _NOT_CALCULATED,  # расход материала
            )
        )
        return PrintProcessCard(part_name=planning_result.part_name, columns=columns, row=row)

    def generate_postprocessing_card(
        self, planning_result: PrintProcessPlanningResult, *, columns: tuple[str, ...]
    ) -> PostprocessingCard:
        # columns: ["№ шага", "Операция", "Оборудование", "Длительность", "Температура"]
        rows = tuple(
            PrintCardRow(
                values=(
                    str(step.sequence_no),
                    step.pp_tooling_type_name + ("" if step.is_required else " (опционально)"),
                    _NOT_CALCULATED,  # конкретное оборудование — не подбирается на этой фазе
                    _NOT_CALCULATED,  # длительность
                    _NOT_CALCULATED,  # температура
                )
            )
            for step in planning_result.postprocessing_steps
        )
        return PostprocessingCard(columns=columns, rows=rows)

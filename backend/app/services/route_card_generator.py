"""Генератор маршрутной карты (Модуль 1.3) из результата автоподбора
техпроцесса (ProcessPlanningResult) и шаблона document_template
(layout_schema из БД НСИ, см. dev/QUESTIONS.md №5).

Автоподбор (Фаза 4, упрощённый) не рассчитывает нормы времени, разряд
работ и не назначает конкретный цех/участок — эти графы шаблона
оставляются пустыми, а не заполняются выдуманными значениями. Полный
расчёт норм — вне объёма этой фазы (требует режимов резания,
см. dev/PLAN.md "Что дальше" в БД НСИ/README.md).
"""

from __future__ import annotations

import json

from app.domain.process_planning.process_model import ProcessPlanningResult
from app.domain.process_planning.route_card_model import RouteCard, RouteCardRow

# Индексы соответствуют порядку из layout_schema.columns:
# ["№ операции", "Код/наименование операции", "Цех", "Уч.", "РМ",
#  "Профессия/разряд", "Оборудование", "Тпз", "Тшт"]
_NOT_CALCULATED = ""  # графа технически применима, но не рассчитывается на этой фазе


class RouteCardGenerator:
    def generate(
        self, planning_result: ProcessPlanningResult, *, columns: tuple[str, ...], gost_form: str | None
    ) -> RouteCard:
        rows = tuple(
            RouteCardRow(
                values=(
                    str(op.sequence_no),
                    f"{op.operation_type_code} {op.operation_type_name}",
                    _NOT_CALCULATED,  # Цех — не определяется автоподбором
                    _NOT_CALCULATED,  # Уч.
                    _NOT_CALCULATED,  # РМ
                    _NOT_CALCULATED,  # Профессия/разряд
                    op.equipment_model_name or "не подобрано",
                    _NOT_CALCULATED,  # Тпз
                    _NOT_CALCULATED,  # Тшт
                )
            )
            for op in planning_result.operations
        )

        technical_requirements = tuple(
            f"{req.text} ({req.reference_standard})"
            if req.reference_standard and req.reference_standard not in req.text
            else req.text
            for req in planning_result.technical_requirements
        )

        return RouteCard(
            part_name=planning_result.part_name,
            material_grade=planning_result.material_grade,
            gost_form=gost_form,
            columns=columns,
            rows=rows,
            technical_requirements=technical_requirements,
        )


def parse_layout_columns(layout_schema_json: str) -> tuple[str, ...]:
    """Разбирает JSON-строку layout_schema (хранится как TEXT в SQLite,
    см. docs/ARCHITECTURE.md "База данных") в кортеж названий столбцов."""
    data = json.loads(layout_schema_json)
    return tuple(data.get("columns", ()))

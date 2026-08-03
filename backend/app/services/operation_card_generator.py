"""Генератор операционной карты (ГОСТ 3.1404-86, Модуль 1.3) из
результата автоподбора техпроцесса (ProcessPlanningResult) — в отличие
от маршрутной карты (route_card_generator.py), заполняет графы режимов
резания t/S/V/n из CuttingModeResult, рассчитанного CuttingModeCalculator
(Фаза 17), когда расчёт возможен. Если для операции расчёт не выполнялся
(нет диаметра заготовки, нет формулы для вида обработки и т.п.) — графы
остаются пустыми, а не заполняются выдуманными значениями; причина
фиксируется в cutting_mode_note для отображения под таблицей.

Норму времени (Тшт/Тв/Тпз) и разряд работы автоподбор не рассчитывает —
требует полного нормирования (хронометраж/типовые нормативы), вне
объёма этой фазы (см. dev/PLAN.md).
"""

from __future__ import annotations

from app.domain.process_planning.operation_card_model import OperationCard, OperationCardRow
from app.domain.process_planning.process_model import ProcessPlanningResult

_NOT_CALCULATED = ""


def _format_number(value: float | None, *, digits: int = 2) -> str:
    if value is None:
        return _NOT_CALCULATED
    return f"{value:.{digits}f}"


class OperationCardGenerator:
    def generate(
        self, planning_result: ProcessPlanningResult, *, columns: tuple[str, ...], gost_form: str | None
    ) -> OperationCard:
        rows = []
        for op in planning_result.operations:
            cm = op.cutting_mode
            tooling = ", ".join(op.tooling_names) if op.tooling_names else "не подобрана"
            values = (
                str(op.sequence_no),
                "1",  # № перехода — упрощённый автоподбор не декомпозирует операцию на переходы
                f"{op.operation_type_code} {op.operation_type_name}",
                op.equipment_model_name or "не подобрано",
                tooling,
                _format_number(cm.depth_of_cut_mm if cm else None, digits=2),
                _format_number(cm.feed_mm_rev if cm else None, digits=2),
                _format_number(cm.cutting_speed_m_min if cm else None, digits=1),
                str(cm.spindle_speed_rpm) if cm and cm.spindle_speed_rpm is not None else _NOT_CALCULATED,
                _NOT_CALCULATED,  # Разряд работы — не рассчитывается
                _format_number(cm.machining_time_min if cm else None, digits=2),
                _NOT_CALCULATED,  # Тв — вспомогательное время, вне объёма
                _NOT_CALCULATED,  # Тшт
                _NOT_CALCULATED,  # Тпз
            )
            rows.append(
                OperationCardRow(
                    values=values[: len(columns)],
                    cutting_mode_note=(cm.source_note if cm and not cm.is_calculated else None),
                )
            )

        return OperationCard(
            part_name=planning_result.part_name,
            material_grade=planning_result.material_grade,
            gost_form=gost_form,
            columns=columns,
            rows=tuple(rows),
        )

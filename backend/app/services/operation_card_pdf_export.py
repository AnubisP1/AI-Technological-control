"""Экспорт операционной карты в PDF по форме ГОСТ 3.1404-86 (форма 3/2а) —
Фаза 17, реальная табличная сетка (см. app/services/gost_pdf_grid.py),
с рассчитанными режимами резания t/S/V/n (CuttingModeCalculator) по
каждой операции, где расчёт был возможен.
"""

from __future__ import annotations

import fitz

from app.domain.process_planning.operation_card_model import OperationCard
from app.services.gost_pdf_grid import GostTableCursor

_GOST_FORM_LABEL = "ГОСТ 3.1404-86, форма 3/2а"

# Ширины граф операционной карты (A4-landscape); индексы соответствуют
# OperationCard.columns: ["№ операции", "№ перехода", "Содержание
# перехода", "Оборудование", "Оснастка", "t", "S", "V", "n",
# "Разряд работы", "То", "Тв", "Тшт", "Тпз"]
_COL_WIDTHS = [32, 32, 165, 105, 105, 30, 30, 38, 40, 55, 35, 35, 35, 35]


def _col_x(start: float, widths: list[float]) -> list[float]:
    xs = [start]
    for w in widths:
        xs.append(xs[-1] + w)
    return xs


def generate_operation_card_pdf(operation_card: OperationCard, *, doc_number: str | None = None) -> bytes:
    doc = fitz.open()
    col_x = _col_x(20, _COL_WIDTHS[: len(operation_card.columns)])

    cursor = GostTableCursor(
        doc,
        col_x=col_x,
        title="Операционная карта",
        gost_form=_GOST_FORM_LABEL,
    )

    cursor.add_note(f"Деталь: {operation_card.part_name or '—'}", bold=True)
    if doc_number:
        cursor.add_note(f"Обозначение документа: {doc_number}", size=9)
    cursor.add_note(f"Материал: {operation_card.material_grade or 'не определён'}", size=9)
    cursor.gap(6)
    cursor.add_note(
        "Разраб.: __________   Провер.: __________   Н.контр.: __________   Утв.: __________", size=8.5
    )
    cursor.gap(10)

    cursor.start_table(list(operation_card.columns))
    notes: list[str] = []
    for row in operation_card.rows:
        cursor.add_row(list(row.values))
        if row.cutting_mode_note:
            op_no = row.values[0] if row.values else "?"
            notes.append(f"Операция {op_no}: режимы резания не рассчитаны — {row.cutting_mode_note}")

    if notes:
        cursor.gap(10)
        cursor.add_note("Примечания к режимам резания", bold=True)
        for note in notes:
            cursor.add_note(note, size=8.5, indent=8)

    return cursor.finish()

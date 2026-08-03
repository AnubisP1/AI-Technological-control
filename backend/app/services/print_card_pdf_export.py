"""Экспорт карты техпроцесса печати (аддитивное производство) в PDF —
Фаза 17. Печать не имеет отраслевого ГОСТ-бланка (в отличие от МК/ОК
металлообработки, ГОСТ 3.1118/3.1404) — оформляется свободной табличной
формой с теми же принципами сетки/кириллицы (app/services/gost_pdf_grid.py),
без штампа Разраб./Провер. по конкретной ГОСТ-форме.

Включает карту техпроцесса печати (технология/принтер/материал/высота
слоя/время/расход — последние три поля из PrintEstimate, Фаза 17,
PrintParameterCalculator), требования к качеству и карту постобработки.
"""

from __future__ import annotations

import fitz

from app.domain.process_planning.print_card_model import PostprocessingCard, PrintProcessCard
from app.services.gost_pdf_grid import GostTableCursor

_PROCESS_COL_WIDTHS = [110, 150, 110, 90, 90, 100, 100]
_POSTPROCESSING_COL_WIDTHS = [50, 160, 160, 90, 90, 220]


def _col_x(start: float, widths: list[float]) -> list[float]:
    xs = [start]
    for w in widths:
        xs.append(xs[-1] + w)
    return xs


def generate_print_card_pdf(
    process_card: PrintProcessCard, postprocessing_card: PostprocessingCard | None = None
) -> bytes:
    doc = fitz.open()
    col_x = _col_x(20, _PROCESS_COL_WIDTHS[: len(process_card.columns)])

    cursor = GostTableCursor(
        doc,
        col_x=col_x,
        title="Карта техпроцесса печати",
        gost_form="Аддитивное производство — свободная форма",
    )
    cursor.add_note(f"Деталь: {process_card.part_name or '—'}", bold=True)
    cursor.gap(6)

    cursor.start_table(list(process_card.columns))
    cursor.add_row(list(process_card.row.values))

    if process_card.print_estimate_note:
        cursor.gap(8)
        cursor.add_note("Источник оценки времени печати и расхода материала", bold=True, size=9.5)
        cursor.add_note(process_card.print_estimate_note, size=8.5, indent=8)

    qs = process_card.quality_standard
    if qs is not None:
        cursor.gap(10)
        cursor.add_note("Требования к качеству", bold=True)
        cursor.add_note(f"Допуск: {qs.tolerance_mm}", size=9, indent=8)
        cursor.add_note(f"Мин. толщина стенки: {qs.min_wall_thickness_mm}", size=9, indent=8)
        cursor.add_note(f"Шероховатость (как напечатано): {qs.roughness_ra_raw_um}", size=9, indent=8)
        if qs.roughness_ra_finished_um:
            cursor.add_note(f"Шероховатость (после обработки): {qs.roughness_ra_finished_um}", size=9, indent=8)
        if qs.min_thread_pitch_mm:
            cursor.add_note(f"Мин. шаг резьбы: {qs.min_thread_pitch_mm}", size=9, indent=8)
        if qs.assembly_clearance_mm:
            cursor.add_note(f"Сборочный зазор: {qs.assembly_clearance_mm}", size=9, indent=8)
        cursor.add_note(qs.source_note, size=8, indent=8)

    if postprocessing_card is not None and postprocessing_card.rows:
        cursor.gap(10)
        cursor.add_note("Карта постобработки", bold=True)
        cursor.gap(4)
        pp_col_x = _col_x(20, _POSTPROCESSING_COL_WIDTHS[: len(postprocessing_card.columns)])
        cursor.start_table(list(postprocessing_card.columns), col_x=pp_col_x)
        for row in postprocessing_card.rows:
            cursor.add_row(list(row.values))

    return cursor.finish()

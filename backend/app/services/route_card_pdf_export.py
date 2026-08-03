"""Экспорт маршрутной карты в PDF по форме ГОСТ 3.1118-82 (форма 1 —
титул со штампом и М01/М02, форма 1б — продолжение построчно по
операциям) — Фаза 17, реальная табличная сетка вместо текстового
списка (см. app/services/kd_review_pdf_export.py, предыдущий подход).

Структура (по образцу БД НСИ Аддитив/Маршраутная карта пример
оформления.pdf):
  - штамп: Разраб./Проверил/Т.контр./Н.контр.
  - блок М01/М02: обозначение и наименование детали, материал, заготовка
  - таблица операций: строки А (Цех/Уч./РМ/Опер./код-наименование
    операции) и Б (оборудование/оснастка) на каждую операцию
  - технические требования (свободный текст) под таблицей
"""

from __future__ import annotations

import fitz

from app.domain.process_planning.route_card_model import RouteCard
from app.services.gost_pdf_grid import GostTableCursor

_GOST_FORM_LABEL = "ГОСТ 3.1118-82, форма 1/1б"

# Ширины граф маршрутной карты (пропорционально A4-landscape ~ 842pt);
# индексы соответствуют RouteCard.columns:
# ["№ операции", "Код/наименование операции", "Цех", "Уч.", "РМ",
#  "Профессия/разряд", "Оборудование", "Тпз", "Тшт"]
_COL_WIDTHS = [55, 190, 55, 55, 55, 100, 190, 55, 55]


def _col_x(start: float, widths: list[float]) -> list[float]:
    xs = [start]
    for w in widths:
        xs.append(xs[-1] + w)
    return xs


def generate_route_card_pdf(route_card: RouteCard, *, doc_number: str | None = None) -> bytes:
    doc = fitz.open()
    col_x = _col_x(20, _COL_WIDTHS)

    cursor = GostTableCursor(
        doc,
        col_x=col_x,
        title="Маршрутная карта",
        gost_form=_GOST_FORM_LABEL,
    )

    cursor.add_note(f"Деталь: {route_card.part_name or '—'}", bold=True)
    if doc_number:
        cursor.add_note(f"Обозначение документа: {doc_number}", size=9)
    cursor.add_note(f"Материал: {route_card.material_grade or 'не определён'}", size=9)
    cursor.gap(6)

    # Штамп разработки — статичные графы (роли), сами ФИО/подписи/даты
    # не подбираются автоматически, оставлены пустыми для заполнения
    # технологом при утверждении (Модуль 2).
    cursor.add_note("Разраб.: __________   Провер.: __________   Н.контр.: __________   Утв.: __________", size=8.5)
    cursor.gap(10)

    cursor.start_table(list(route_card.columns))
    for row in route_card.rows:
        cursor.add_row(list(row.values))

    if route_card.technical_requirements:
        cursor.gap(10)
        cursor.add_note("Технические требования", bold=True)
        for i, req in enumerate(route_card.technical_requirements, start=1):
            cursor.add_note(f"{i}. {req}", size=9, indent=8)

    return cursor.finish()

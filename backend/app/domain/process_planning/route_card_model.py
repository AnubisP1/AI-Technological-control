"""Доменная модель маршрутной карты (ГОСТ 3.1118-82) — печатное
представление подобранного техпроцесса. Столбцы берутся из
document_template.layout_schema (см. dev/QUESTIONS.md №5), а не
захардкожены здесь — так карта переживает правки состава граф в БД
без изменения кода генератора.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RouteCardRow:
    """Одна строка маршрутной карты — значения уже сопоставлены со
    столбцами шаблона по порядку (см. RouteCard.columns)."""

    values: tuple[str, ...]


@dataclass(frozen=True)
class RouteCard:
    part_name: str | None
    material_grade: str | None
    gost_form: str | None
    columns: tuple[str, ...]
    rows: tuple[RouteCardRow, ...]

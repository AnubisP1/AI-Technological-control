"""Доменная модель операционной карты (ГОСТ 3.1404-86) — печатное
представление подобранного техпроцесса с рассчитанными режимами
резания (Фаза 17, CuttingModeCalculator). Столбцы берутся из
document_template.layout_schema (код 'OK'), как и в маршрутной карте
(см. route_card_model.py) — не захардкожены здесь.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OperationCardRow:
    """Одна строка операционной карты — значения уже сопоставлены со
    столбцами шаблона по порядку (см. OperationCard.columns)."""

    values: tuple[str, ...]
    cutting_mode_note: str | None = None  # источник/причина отсутствия расчёта режимов для этой строки


@dataclass(frozen=True)
class OperationCard:
    part_name: str | None
    material_grade: str | None
    gost_form: str | None
    columns: tuple[str, ...]
    rows: tuple[OperationCardRow, ...]

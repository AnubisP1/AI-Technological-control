"""Доменные модели карты техпроцесса печати и карты постобработки
(ГОСТ-аналоги для аддитивных технологий, Модуль 1.3, пластик).
Столбцы берутся из am_document_template.layout_schema, как и для
маршрутной карты металла — не хардкодятся в генераторе."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PrintCardRow:
    values: tuple[str, ...]


@dataclass(frozen=True)
class QualityStandardInfo:
    tolerance_mm: str
    min_wall_thickness_mm: str
    roughness_ra_raw_um: str
    roughness_ra_finished_um: str | None
    min_thread_pitch_mm: str | None
    assembly_clearance_mm: str | None
    source_note: str


@dataclass(frozen=True)
class PrintProcessCard:
    part_name: str | None
    columns: tuple[str, ...]
    row: PrintCardRow
    quality_standard: QualityStandardInfo | None = None
    print_estimate_note: str | None = None  # источник оценки времени/расхода (Фаза 17), None — не рассчитано


@dataclass(frozen=True)
class PostprocessingCard:
    columns: tuple[str, ...]
    rows: tuple[PrintCardRow, ...]

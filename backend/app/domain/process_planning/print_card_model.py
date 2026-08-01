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
class PrintProcessCard:
    part_name: str | None
    columns: tuple[str, ...]
    row: PrintCardRow


@dataclass(frozen=True)
class PostprocessingCard:
    columns: tuple[str, ...]
    rows: tuple[PrintCardRow, ...]

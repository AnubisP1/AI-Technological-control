"""Порт доступа к справочным данным НСИ, нужным для сверки КД (Модуль 1.2).
Не весь nsi_db — только то, что нужно этому сервису, чтобы domain не
зависел от деталей схемы SQLite."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class MaterialRecord:
    grade: str
    gost_standard: str | None
    # Технологические свойства (Фаза 18 — нужны LLM для реальной аналитики
    # технологичности "материал X обрабатывается хуже, вот аналог с лучшей
    # обрабатываемостью", а не только для сверки марка+ГОСТ). Опциональны
    # с дефолтом None, чтобы не ломать существующие вызовы с моковыми
    # записями в тестах, где эти поля не нужны.
    density_kg_m3: float | None = None
    tensile_strength_mpa: float | None = None
    hardness_hb: float | None = None
    machinability_index: float | None = None
    # Расширенный справочник марок сталей (2026-08-04) — твёрдость по
    # Роквеллу и красностойкость нужны для инструментальных/быстрорежущих/
    # подшипниковых сталей, где HB не применяется (закалка на высокую
    # твёрдость); химсостав/термообработка/применение дают LLM реальный
    # материал для сравнения марок, а не только 4 числа.
    hardness_hrc: float | None = None
    red_hardness_c: float | None = None
    chemical_composition: str | None = None
    heat_treatment: str | None = None
    application: str | None = None


@dataclass(frozen=True)
class WorkpieceBlankRecord:
    designation: str
    gost_standard: str | None
    diameter_mm: float | None


class INsiLookup(Protocol):
    def find_materials(self) -> tuple[MaterialRecord, ...]: ...
    def find_workpiece_blanks(self) -> tuple[WorkpieceBlankRecord, ...]: ...

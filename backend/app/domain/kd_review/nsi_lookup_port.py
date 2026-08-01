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


@dataclass(frozen=True)
class WorkpieceBlankRecord:
    designation: str
    gost_standard: str | None
    diameter_mm: float | None


class INsiLookup(Protocol):
    def find_materials(self) -> tuple[MaterialRecord, ...]: ...
    def find_workpiece_blanks(self) -> tuple[WorkpieceBlankRecord, ...]: ...

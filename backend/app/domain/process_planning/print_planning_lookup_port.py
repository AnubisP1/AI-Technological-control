"""Порт доступа к данным additive-НСИ, нужным для автоподбора
техпроцесса печати (Модуль 1.3, пластик)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class AmMaterialGroupRecord:
    id: int
    code: str
    name: str
    am_technology_id: int


@dataclass(frozen=True)
class PrinterTypeRecord:
    id: int
    code: str
    name: str


@dataclass(frozen=True)
class PrinterModelRecord:
    id: int
    printer_type_id: int
    model_name: str


@dataclass(frozen=True)
class PpToolingStepRecord:
    pp_tooling_type_id: int
    pp_tooling_type_name: str
    is_required: bool
    typical_order: int | None


class IPrintPlanningLookup(Protocol):
    def find_am_technology_id_by_code(self, code: str) -> int | None: ...
    def find_material_group(
        self, am_technology_id: int, material_group_code: str
    ) -> AmMaterialGroupRecord | None: ...
    def find_printer_types_for_material_group(
        self, am_material_group_id: int
    ) -> tuple[PrinterTypeRecord, ...]: ...
    def find_printer_model_for_type(self, printer_type_id: int) -> PrinterModelRecord | None: ...
    def find_postprocessing_steps_for_material_group(
        self, am_material_group_id: int
    ) -> tuple[PpToolingStepRecord, ...]: ...

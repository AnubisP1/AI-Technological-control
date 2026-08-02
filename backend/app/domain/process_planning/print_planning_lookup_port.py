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


@dataclass(frozen=True)
class TechnologyToleranceRecord:
    tolerance_min_mm: float
    tolerance_max_mm: float
    min_wall_thickness_mm: float
    max_wall_thickness_mm: float | None
    roughness_ra_raw_min_um: float
    roughness_ra_raw_max_um: float
    roughness_ra_finished_min_um: float | None
    roughness_ra_finished_max_um: float | None
    min_thread_pitch_mm: float | None
    assembly_clearance_min_mm: float | None
    assembly_clearance_max_mm: float | None
    source_note: str


@dataclass(frozen=True)
class PostprocessingEffectRecord:
    method_name: str
    tolerance_improvement_min_percent: float
    tolerance_improvement_max_percent: float
    roughness_reduction_factor_min: float
    roughness_reduction_factor_max: float


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
    def find_technology_tolerance(
        self, am_technology_id: int
    ) -> TechnologyToleranceRecord | None: ...
    def find_postprocessing_effect_for_tooling_type(
        self, pp_tooling_type_id: int
    ) -> PostprocessingEffectRecord | None: ...

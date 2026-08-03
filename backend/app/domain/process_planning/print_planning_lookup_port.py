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
    layer_resolution_min_mm: float
    layer_resolution_max_mm: float
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


@dataclass(frozen=True)
class PartApplicationClassRecord:
    id: int
    code: str
    name: str
    description: str | None


@dataclass(frozen=True)
class OperatingConditionRecord:
    id: int
    condition_type: str
    code: str
    name: str
    range_min: float | None
    range_max: float | None
    unit: str | None
    description: str | None


@dataclass(frozen=True)
class MaterialDensityRecord:
    density_g_cm3: float


@dataclass(frozen=True)
class PrintSpeedReferenceRecord:
    volumetric_rate_mm3_s: float
    source: str


@dataclass(frozen=True)
class MaterialRecommendationRow:
    priority: int
    am_technology_code: str
    am_technology_name: str
    material_group_code: str
    material_group_name: str
    rationale: str
    source_type: str
    source_title: str
    source_reliability: str
    min_infill_percent: float | None
    recommended_wall_count: int | None
    orientation_note: str | None


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
    def find_part_application_classes(self) -> tuple[PartApplicationClassRecord, ...]: ...
    def find_part_application_class_by_code(
        self, code: str
    ) -> PartApplicationClassRecord | None: ...
    def find_operating_conditions(
        self, part_application_class_id: int | None = None
    ) -> tuple[OperatingConditionRecord, ...]: ...
    def find_operating_condition_ids_by_codes(self, codes: tuple[str, ...]) -> dict[str, int]: ...
    def find_material_recommendations(
        self, part_application_class_id: int, operating_condition_ids: tuple[int, ...]
    ) -> tuple[MaterialRecommendationRow, ...]: ...
    def find_material_density(self, am_material_group_id: int) -> MaterialDensityRecord | None: ...
    def find_print_speed_reference(
        self, am_technology_id: int
    ) -> PrintSpeedReferenceRecord | None: ...

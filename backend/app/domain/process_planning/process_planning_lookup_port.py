"""Порт доступа к данным НСИ, нужным для автоподбора техпроцесса
(Модуль 1.3). Изолирует domain от деталей схемы SQLite."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class EquipmentTypeRecord:
    id: int
    code: str
    name: str


@dataclass(frozen=True)
class OperationTypeRecord:
    id: int
    code: str
    name: str


@dataclass(frozen=True)
class EquipmentModelRecord:
    id: int
    equipment_type_id: int
    model_name: str
    spindle_speed_min_rpm: int | None = None
    spindle_speed_max_rpm: int | None = None


@dataclass(frozen=True)
class ToolingTypeRecord:
    id: int
    name: str


@dataclass(frozen=True)
class MachiningRequirementRecord:
    code: str
    formulation_template: str
    reference_standard: str | None
    notes: str | None


@dataclass(frozen=True)
class SurfaceHardeningMethodRecord:
    method_name: str
    reference_instruction: str
    applicable_to: str | None


@dataclass(frozen=True)
class CuttingModeFormulaRecord:
    tool_life_min: float
    cv: float
    m: float
    xv: float
    yv: float
    source: str


@dataclass(frozen=True)
class FeedReferenceRecord:
    feed_mm_rev_min: float
    feed_mm_rev_max: float
    depth_of_cut_mm_min: float | None
    depth_of_cut_mm_max: float | None
    source: str


@dataclass(frozen=True)
class MaterialMachinabilityRecord:
    machinability_index: float


class IProcessPlanningLookup(Protocol):
    def find_material_group_id(self, material_grade: str) -> int | None: ...
    def find_workpiece_type_id_by_code(self, code: str) -> int | None: ...
    def find_equipment_types_for_material_and_workpiece(
        self, material_group_id: int, workpiece_type_id: int
    ) -> tuple[EquipmentTypeRecord, ...]: ...
    def find_operation_types_for_equipment_type(
        self, equipment_type_id: int
    ) -> tuple[OperationTypeRecord, ...]: ...
    def find_equipment_model_for_type(
        self, equipment_type_id: int
    ) -> EquipmentModelRecord | None: ...
    def find_tooling_types_for_operation_type(
        self, operation_type_id: int
    ) -> tuple[ToolingTypeRecord, ...]: ...
    def find_operation_type_id_by_code(self, code: str) -> int | None: ...
    def find_machining_requirements_for_operation_types(
        self, operation_type_ids: tuple[int, ...]
    ) -> tuple[MachiningRequirementRecord, ...]: ...
    def find_surface_hardening_methods_for_material_group(
        self, material_group_id: int
    ) -> tuple[SurfaceHardeningMethodRecord, ...]: ...
    def find_cutting_mode_formula(
        self, operation_type_id: int
    ) -> CuttingModeFormulaRecord | None: ...
    def find_feed_reference(
        self, operation_type_id: int, material_group_id: int
    ) -> FeedReferenceRecord | None: ...
    def find_material_machinability(
        self, material_group_id: int
    ) -> MaterialMachinabilityRecord | None: ...

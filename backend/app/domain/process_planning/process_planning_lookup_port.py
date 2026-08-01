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


@dataclass(frozen=True)
class ToolingTypeRecord:
    id: int
    name: str


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

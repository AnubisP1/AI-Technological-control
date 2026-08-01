"""SQLite-реализация IProcessPlanningLookup для автоподбора техпроцесса
(Модуль 1.3) поверх metal.sqlite."""

from __future__ import annotations

from pathlib import Path

from app.domain.material_text import extract_grade_part, normalize_grade
from app.domain.process_planning.process_planning_lookup_port import (
    EquipmentModelRecord,
    EquipmentTypeRecord,
    OperationTypeRecord,
    ToolingTypeRecord,
)
from app.infrastructure.db.nsi_db import connect


class SqliteProcessPlanningLookup:
    def __init__(self, metal_db_path: Path) -> None:
        self._metal_db_path = metal_db_path

    def find_material_group_id(self, material_grade: str) -> int | None:
        connection = connect(self._metal_db_path)
        try:
            target = normalize_grade(extract_grade_part(material_grade))
            rows = connection.execute("SELECT grade, material_group_id FROM material").fetchall()
            for row in rows:
                if normalize_grade(row["grade"]) == target:
                    return row["material_group_id"]
            return None
        finally:
            connection.close()

    def find_workpiece_type_id_by_code(self, code: str) -> int | None:
        connection = connect(self._metal_db_path)
        try:
            row = connection.execute(
                "SELECT id FROM workpiece_type WHERE code = ?", (code,)
            ).fetchone()
            return row["id"] if row else None
        finally:
            connection.close()

    def find_equipment_types_for_material_and_workpiece(
        self, material_group_id: int, workpiece_type_id: int
    ) -> tuple[EquipmentTypeRecord, ...]:
        connection = connect(self._metal_db_path)
        try:
            rows = connection.execute(
                """
                SELECT DISTINCT et.id, et.code, et.name
                FROM equipment_type et
                JOIN equipment_type_material_group mg ON mg.equipment_type_id = et.id
                JOIN equipment_type_workpiece_type wt ON wt.equipment_type_id = et.id
                WHERE mg.material_group_id = ? AND wt.workpiece_type_id = ?
                """,
                (material_group_id, workpiece_type_id),
            ).fetchall()
            return tuple(
                EquipmentTypeRecord(id=row["id"], code=row["code"], name=row["name"])
                for row in rows
            )
        finally:
            connection.close()

    def find_operation_types_for_equipment_type(
        self, equipment_type_id: int
    ) -> tuple[OperationTypeRecord, ...]:
        connection = connect(self._metal_db_path)
        try:
            rows = connection.execute(
                """
                SELECT ot.id, ot.code, ot.name
                FROM operation_type ot
                JOIN equipment_type_operation_type eot ON eot.operation_type_id = ot.id
                WHERE eot.equipment_type_id = ?
                """,
                (equipment_type_id,),
            ).fetchall()
            return tuple(
                OperationTypeRecord(id=row["id"], code=row["code"], name=row["name"])
                for row in rows
            )
        finally:
            connection.close()

    def find_equipment_model_for_type(
        self, equipment_type_id: int
    ) -> EquipmentModelRecord | None:
        connection = connect(self._metal_db_path)
        try:
            row = connection.execute(
                "SELECT id, equipment_type_id, model_name FROM equipment_model "
                "WHERE equipment_type_id = ? LIMIT 1",
                (equipment_type_id,),
            ).fetchone()
            if row is None:
                return None
            return EquipmentModelRecord(
                id=row["id"],
                equipment_type_id=row["equipment_type_id"],
                model_name=row["model_name"],
            )
        finally:
            connection.close()

    def find_tooling_types_for_operation_type(
        self, operation_type_id: int
    ) -> tuple[ToolingTypeRecord, ...]:
        connection = connect(self._metal_db_path)
        try:
            rows = connection.execute(
                """
                SELECT tt.id, tt.name
                FROM tooling_type tt
                JOIN operation_type_tooling_type ott ON ott.tooling_type_id = tt.id
                WHERE ott.operation_type_id = ?
                """,
                (operation_type_id,),
            ).fetchall()
            return tuple(ToolingTypeRecord(id=row["id"], name=row["name"]) for row in rows)
        finally:
            connection.close()

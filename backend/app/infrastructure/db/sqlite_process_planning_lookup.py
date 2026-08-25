"""SQLite-реализация IProcessPlanningLookup для автоподбора техпроцесса
(Модуль 1.3) поверх metal.sqlite."""

from __future__ import annotations

from pathlib import Path

from app.domain.material_text import extract_grade_part, normalize_grade
from app.domain.process_planning.process_planning_lookup_port import (
    CuttingModeFormulaRecord,
    EquipmentModelRecord,
    EquipmentTypeRecord,
    FeedReferenceRecord,
    MachiningRequirementRecord,
    MaterialMachinabilityRecord,
    OperationTypeRecord,
    SurfaceHardeningMethodRecord,
    ToolingRecord,
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
                "SELECT id, equipment_type_id, model_name, "
                "spindle_speed_min_rpm, spindle_speed_max_rpm FROM equipment_model "
                "WHERE equipment_type_id = ? LIMIT 1",
                (equipment_type_id,),
            ).fetchone()
            if row is None:
                return None
            return EquipmentModelRecord(
                id=row["id"],
                equipment_type_id=row["equipment_type_id"],
                model_name=row["model_name"],
                spindle_speed_min_rpm=row["spindle_speed_min_rpm"],
                spindle_speed_max_rpm=row["spindle_speed_max_rpm"],
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

    def find_operation_type_id_by_code(self, code: str) -> int | None:
        connection = connect(self._metal_db_path)
        try:
            row = connection.execute(
                "SELECT id FROM operation_type WHERE code = ?", (code,)
            ).fetchone()
            return row["id"] if row else None
        finally:
            connection.close()

    def find_machining_requirements_for_operation_types(
        self, operation_type_ids: tuple[int, ...]
    ) -> tuple[MachiningRequirementRecord, ...]:
        connection = connect(self._metal_db_path)
        try:
            placeholders = ",".join("?" for _ in operation_type_ids)
            rows = connection.execute(
                f"""
                SELECT code, formulation_template, reference_standard, notes
                FROM machining_requirement_template
                WHERE operation_type_id IS NULL
                   OR operation_type_id IN ({placeholders})
                """,
                operation_type_ids,
            ).fetchall()
            return tuple(
                MachiningRequirementRecord(
                    code=row["code"],
                    formulation_template=row["formulation_template"],
                    reference_standard=row["reference_standard"],
                    notes=row["notes"],
                )
                for row in rows
            )
        finally:
            connection.close()

    def find_surface_hardening_methods_for_material_group(
        self, material_group_id: int
    ) -> tuple[SurfaceHardeningMethodRecord, ...]:
        connection = connect(self._metal_db_path)
        try:
            rows = connection.execute(
                """
                SELECT method_name, reference_instruction, applicable_to
                FROM surface_hardening_method
                WHERE material_group_id IS NULL OR material_group_id = ?
                """,
                (material_group_id,),
            ).fetchall()
            return tuple(
                SurfaceHardeningMethodRecord(
                    method_name=row["method_name"],
                    reference_instruction=row["reference_instruction"],
                    applicable_to=row["applicable_to"],
                )
                for row in rows
            )
        finally:
            connection.close()

    def find_cutting_mode_formula(
        self, operation_type_id: int
    ) -> CuttingModeFormulaRecord | None:
        connection = connect(self._metal_db_path)
        try:
            row = connection.execute(
                """
                SELECT tool_life_min, cv, m, xv, yv, source
                FROM cutting_mode_formula
                WHERE operation_type_id = ?
                LIMIT 1
                """,
                (operation_type_id,),
            ).fetchone()
            if row is None:
                return None
            return CuttingModeFormulaRecord(
                tool_life_min=row["tool_life_min"],
                cv=row["cv"],
                m=row["m"],
                xv=row["xv"],
                yv=row["yv"],
                source=row["source"],
            )
        finally:
            connection.close()

    def find_feed_reference(
        self, operation_type_id: int, material_group_id: int
    ) -> FeedReferenceRecord | None:
        connection = connect(self._metal_db_path)
        try:
            row = connection.execute(
                """
                SELECT feed_mm_rev_min, feed_mm_rev_max,
                       depth_of_cut_mm_min, depth_of_cut_mm_max, source
                FROM feed_reference
                WHERE operation_type_id = ? AND material_group_id = ?
                """,
                (operation_type_id, material_group_id),
            ).fetchone()
            if row is None:
                return None
            return FeedReferenceRecord(
                feed_mm_rev_min=row["feed_mm_rev_min"],
                feed_mm_rev_max=row["feed_mm_rev_max"],
                depth_of_cut_mm_min=row["depth_of_cut_mm_min"],
                depth_of_cut_mm_max=row["depth_of_cut_mm_max"],
                source=row["source"],
            )
        finally:
            connection.close()

    def find_material_machinability(
        self, material_group_id: int
    ) -> MaterialMachinabilityRecord | None:
        connection = connect(self._metal_db_path)
        try:
            row = connection.execute(
                "SELECT machinability_index FROM material_group WHERE id = ?",
                (material_group_id,),
            ).fetchone()
            if row is None:
                return None
            return MaterialMachinabilityRecord(machinability_index=row["machinability_index"])
        finally:
            connection.close()

    def find_tooling_by_type_code(self, tooling_type_code: str) -> tuple[ToolingRecord, ...]:
        connection = connect(self._metal_db_path)
        try:
            rows = connection.execute(
                """
                SELECT tooling.id, tooling.designation, tooling.diameter_mm
                FROM tooling
                JOIN tooling_type ON tooling_type.id = tooling.tooling_type_id
                WHERE tooling_type.code = ? AND tooling.diameter_mm IS NOT NULL
                """,
                (tooling_type_code,),
            ).fetchall()
            return tuple(
                ToolingRecord(id=row["id"], designation=row["designation"], diameter_mm=row["diameter_mm"])
                for row in rows
            )
        finally:
            connection.close()

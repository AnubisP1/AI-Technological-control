"""SQLite-реализация IPrintPlanningLookup для автоподбора техпроцесса
печати (Модуль 1.3, пластик) поверх additive.sqlite."""

from __future__ import annotations

from pathlib import Path

from app.domain.process_planning.print_planning_lookup_port import (
    AmMaterialGroupRecord,
    PostprocessingEffectRecord,
    PpToolingStepRecord,
    PrinterModelRecord,
    PrinterTypeRecord,
    TechnologyToleranceRecord,
)
from app.infrastructure.db.nsi_db import connect


class SqlitePrintPlanningLookup:
    def __init__(self, additive_db_path: Path) -> None:
        self._additive_db_path = additive_db_path

    def find_am_technology_id_by_code(self, code: str) -> int | None:
        connection = connect(self._additive_db_path)
        try:
            row = connection.execute(
                "SELECT id FROM am_technology WHERE code = ?", (code,)
            ).fetchone()
            return row["id"] if row else None
        finally:
            connection.close()

    def find_material_group(
        self, am_technology_id: int, material_group_code: str
    ) -> AmMaterialGroupRecord | None:
        connection = connect(self._additive_db_path)
        try:
            row = connection.execute(
                "SELECT id, code, name, am_technology_id FROM am_material_group "
                "WHERE am_technology_id = ? AND code = ?",
                (am_technology_id, material_group_code),
            ).fetchone()
            if row is None:
                return None
            return AmMaterialGroupRecord(
                id=row["id"],
                code=row["code"],
                name=row["name"],
                am_technology_id=row["am_technology_id"],
            )
        finally:
            connection.close()

    def find_printer_types_for_material_group(
        self, am_material_group_id: int
    ) -> tuple[PrinterTypeRecord, ...]:
        connection = connect(self._additive_db_path)
        try:
            rows = connection.execute(
                """
                SELECT pt.id, pt.code, pt.name
                FROM printer_type pt
                JOIN printer_type_material_group ptmg ON ptmg.printer_type_id = pt.id
                WHERE ptmg.am_material_group_id = ?
                """,
                (am_material_group_id,),
            ).fetchall()
            return tuple(
                PrinterTypeRecord(id=row["id"], code=row["code"], name=row["name"])
                for row in rows
            )
        finally:
            connection.close()

    def find_printer_model_for_type(self, printer_type_id: int) -> PrinterModelRecord | None:
        connection = connect(self._additive_db_path)
        try:
            row = connection.execute(
                "SELECT id, printer_type_id, model_name FROM printer_model "
                "WHERE printer_type_id = ? LIMIT 1",
                (printer_type_id,),
            ).fetchone()
            if row is None:
                return None
            return PrinterModelRecord(
                id=row["id"],
                printer_type_id=row["printer_type_id"],
                model_name=row["model_name"],
            )
        finally:
            connection.close()

    def find_postprocessing_steps_for_material_group(
        self, am_material_group_id: int
    ) -> tuple[PpToolingStepRecord, ...]:
        connection = connect(self._additive_db_path)
        try:
            rows = connection.execute(
                """
                SELECT pt.id AS pp_tooling_type_id, pt.name AS pp_tooling_type_name,
                       mgt.is_required, mgt.typical_order
                FROM pp_tooling_type pt
                JOIN material_group_pp_tooling_type mgt ON mgt.pp_tooling_type_id = pt.id
                WHERE mgt.am_material_group_id = ?
                """,
                (am_material_group_id,),
            ).fetchall()
            return tuple(
                PpToolingStepRecord(
                    pp_tooling_type_id=row["pp_tooling_type_id"],
                    pp_tooling_type_name=row["pp_tooling_type_name"],
                    is_required=bool(row["is_required"]),
                    typical_order=row["typical_order"],
                )
                for row in rows
            )
        finally:
            connection.close()

    def find_technology_tolerance(self, am_technology_id: int) -> TechnologyToleranceRecord | None:
        connection = connect(self._additive_db_path)
        try:
            row = connection.execute(
                """
                SELECT tolerance_min_mm, tolerance_max_mm,
                       min_wall_thickness_mm, max_wall_thickness_mm,
                       roughness_ra_raw_min_um, roughness_ra_raw_max_um,
                       roughness_ra_finished_min_um, roughness_ra_finished_max_um,
                       min_thread_pitch_mm, assembly_clearance_min_mm, assembly_clearance_max_mm,
                       source_note
                FROM am_technology_tolerance
                WHERE am_technology_id = ?
                """,
                (am_technology_id,),
            ).fetchone()
            if row is None:
                return None
            return TechnologyToleranceRecord(
                tolerance_min_mm=row["tolerance_min_mm"],
                tolerance_max_mm=row["tolerance_max_mm"],
                min_wall_thickness_mm=row["min_wall_thickness_mm"],
                max_wall_thickness_mm=row["max_wall_thickness_mm"],
                roughness_ra_raw_min_um=row["roughness_ra_raw_min_um"],
                roughness_ra_raw_max_um=row["roughness_ra_raw_max_um"],
                roughness_ra_finished_min_um=row["roughness_ra_finished_min_um"],
                roughness_ra_finished_max_um=row["roughness_ra_finished_max_um"],
                min_thread_pitch_mm=row["min_thread_pitch_mm"],
                assembly_clearance_min_mm=row["assembly_clearance_min_mm"],
                assembly_clearance_max_mm=row["assembly_clearance_max_mm"],
                source_note=row["source_note"],
            )
        finally:
            connection.close()

    def find_postprocessing_effect_for_tooling_type(
        self, pp_tooling_type_id: int
    ) -> PostprocessingEffectRecord | None:
        connection = connect(self._additive_db_path)
        try:
            row = connection.execute(
                """
                SELECT method_name, tolerance_improvement_min_percent,
                       tolerance_improvement_max_percent,
                       roughness_reduction_factor_min, roughness_reduction_factor_max
                FROM postprocessing_quality_effect
                WHERE pp_tooling_type_id = ?
                LIMIT 1
                """,
                (pp_tooling_type_id,),
            ).fetchone()
            if row is None:
                return None
            return PostprocessingEffectRecord(
                method_name=row["method_name"],
                tolerance_improvement_min_percent=row["tolerance_improvement_min_percent"],
                tolerance_improvement_max_percent=row["tolerance_improvement_max_percent"],
                roughness_reduction_factor_min=row["roughness_reduction_factor_min"],
                roughness_reduction_factor_max=row["roughness_reduction_factor_max"],
            )
        finally:
            connection.close()

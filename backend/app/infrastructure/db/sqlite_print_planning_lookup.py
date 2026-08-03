"""SQLite-реализация IPrintPlanningLookup для автоподбора техпроцесса
печати (Модуль 1.3, пластик) поверх additive.sqlite."""

from __future__ import annotations

from pathlib import Path

from app.domain.process_planning.print_planning_lookup_port import (
    AmMaterialGroupRecord,
    MaterialDensityRecord,
    MaterialRecommendationRow,
    OperatingConditionRecord,
    PartApplicationClassRecord,
    PostprocessingEffectRecord,
    PpToolingStepRecord,
    PrinterModelRecord,
    PrinterTypeRecord,
    PrintSpeedReferenceRecord,
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
                       layer_resolution_min_mm, layer_resolution_max_mm,
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
                layer_resolution_min_mm=row["layer_resolution_min_mm"],
                layer_resolution_max_mm=row["layer_resolution_max_mm"],
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

    def find_part_application_classes(self) -> tuple[PartApplicationClassRecord, ...]:
        connection = connect(self._additive_db_path)
        try:
            rows = connection.execute(
                "SELECT id, code, name, description FROM part_application_class ORDER BY id"
            ).fetchall()
            return tuple(
                PartApplicationClassRecord(
                    id=row["id"],
                    code=row["code"],
                    name=row["name"],
                    description=row["description"],
                )
                for row in rows
            )
        finally:
            connection.close()

    def find_part_application_class_by_code(
        self, code: str
    ) -> PartApplicationClassRecord | None:
        connection = connect(self._additive_db_path)
        try:
            row = connection.execute(
                "SELECT id, code, name, description FROM part_application_class WHERE code = ?",
                (code,),
            ).fetchone()
            if row is None:
                return None
            return PartApplicationClassRecord(
                id=row["id"], code=row["code"], name=row["name"], description=row["description"]
            )
        finally:
            connection.close()

    def find_operating_conditions(
        self, part_application_class_id: int | None = None
    ) -> tuple[OperatingConditionRecord, ...]:
        connection = connect(self._additive_db_path)
        try:
            if part_application_class_id is None:
                rows = connection.execute(
                    """
                    SELECT id, condition_type, code, name, range_min, range_max, unit, description
                    FROM operating_condition
                    ORDER BY condition_type, id
                    """
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT oc.id, oc.condition_type, oc.code, oc.name, oc.range_min, oc.range_max,
                           oc.unit, oc.description
                    FROM operating_condition oc
                    JOIN part_application_class_typical_condition tc
                        ON tc.operating_condition_id = oc.id
                    WHERE tc.part_application_class_id = ?
                    ORDER BY oc.condition_type, oc.id
                    """,
                    (part_application_class_id,),
                ).fetchall()
            return tuple(
                OperatingConditionRecord(
                    id=row["id"],
                    condition_type=row["condition_type"],
                    code=row["code"],
                    name=row["name"],
                    range_min=row["range_min"],
                    range_max=row["range_max"],
                    unit=row["unit"],
                    description=row["description"],
                )
                for row in rows
            )
        finally:
            connection.close()

    def find_operating_condition_ids_by_codes(self, codes: tuple[str, ...]) -> dict[str, int]:
        """Возвращает только реально найденные код->id соответствия — код,
        отсутствующий в результирующем словаре, значит не найден в
        справочнике (вызывающий сервис явно предупреждает об этом,
        а не подменяет отсутствие тихим пропуском)."""
        if not codes:
            return {}
        connection = connect(self._additive_db_path)
        try:
            placeholders = ",".join("?" for _ in codes)
            rows = connection.execute(
                f"SELECT code, id FROM operating_condition WHERE code IN ({placeholders})",
                codes,
            ).fetchall()
            return {row["code"]: row["id"] for row in rows}
        finally:
            connection.close()

    def find_material_recommendations(
        self, part_application_class_id: int, operating_condition_ids: tuple[int, ...]
    ) -> tuple[MaterialRecommendationRow, ...]:
        """operating_condition_ids пустой — возвращает базовые рекомендации
        (operating_condition_id IS NULL в БД), не привязанные к конкретным
        условиям эксплуатации. Откат с условий на базовые при пустом
        результате — ответственность вызывающего сервиса (там же явный
        warning), не этого метода: лукап отражает ровно то, что нашёл."""
        connection = connect(self._additive_db_path)
        try:
            if operating_condition_ids:
                placeholders = ",".join("?" for _ in operating_condition_ids)
                condition_clause = f"amr.operating_condition_id IN ({placeholders})"
                params: tuple = (part_application_class_id, *operating_condition_ids)
            else:
                condition_clause = "amr.operating_condition_id IS NULL"
                params = (part_application_class_id,)

            rows = connection.execute(
                f"""
                SELECT amr.priority, amr.rationale, amr.min_infill_percent,
                       amr.recommended_wall_count, amr.orientation_note,
                       amg.code AS material_group_code, amg.name AS material_group_name,
                       t.code AS am_technology_code, t.name AS am_technology_name,
                       rs.source_type, rs.title AS source_title, rs.reliability AS source_reliability
                FROM application_material_recommendation amr
                JOIN am_material_group amg ON amg.id = amr.am_material_group_id
                JOIN am_technology t ON t.id = amr.am_technology_id
                JOIN recommendation_source rs ON rs.id = amr.recommendation_source_id
                WHERE amr.part_application_class_id = ?
                  AND {condition_clause}
                ORDER BY amr.priority
                """,
                params,
            ).fetchall()
            return tuple(
                MaterialRecommendationRow(
                    priority=row["priority"],
                    am_technology_code=row["am_technology_code"],
                    am_technology_name=row["am_technology_name"],
                    material_group_code=row["material_group_code"],
                    material_group_name=row["material_group_name"],
                    rationale=row["rationale"],
                    source_type=row["source_type"],
                    source_title=row["source_title"],
                    source_reliability=row["source_reliability"],
                    min_infill_percent=row["min_infill_percent"],
                    recommended_wall_count=row["recommended_wall_count"],
                    orientation_note=row["orientation_note"],
                )
                for row in rows
            )
        finally:
            connection.close()

    def find_material_density(self, am_material_group_id: int) -> MaterialDensityRecord | None:
        # am_material_group -> am_material в текущих данных всегда 1:1
        # (см. seed_data.sql) — если группа получит несколько марок с
        # разной плотностью, здесь понадобится уточнение по конкретной
        # марке, а не по группе; пока это не требуется.
        connection = connect(self._additive_db_path)
        try:
            row = connection.execute(
                "SELECT density_g_cm3 FROM am_material "
                "WHERE am_material_group_id = ? AND density_g_cm3 IS NOT NULL LIMIT 1",
                (am_material_group_id,),
            ).fetchone()
            if row is None:
                return None
            return MaterialDensityRecord(density_g_cm3=row["density_g_cm3"])
        finally:
            connection.close()

    def find_print_speed_reference(
        self, am_technology_id: int
    ) -> PrintSpeedReferenceRecord | None:
        connection = connect(self._additive_db_path)
        try:
            row = connection.execute(
                "SELECT volumetric_rate_mm3_s, source FROM print_speed_reference "
                "WHERE am_technology_id = ?",
                (am_technology_id,),
            ).fetchone()
            if row is None:
                return None
            return PrintSpeedReferenceRecord(
                volumetric_rate_mm3_s=row["volumetric_rate_mm3_s"], source=row["source"]
            )
        finally:
            connection.close()

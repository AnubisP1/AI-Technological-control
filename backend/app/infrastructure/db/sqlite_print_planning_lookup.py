"""SQLite-реализация IPrintPlanningLookup для автоподбора техпроцесса
печати (Модуль 1.3, пластик) поверх additive.sqlite."""

from __future__ import annotations

from pathlib import Path

from app.domain.process_planning.print_planning_lookup_port import (
    AmMaterialGroupRecord,
    PpToolingStepRecord,
    PrinterModelRecord,
    PrinterTypeRecord,
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

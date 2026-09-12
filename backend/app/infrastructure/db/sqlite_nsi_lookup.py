"""SQLite-реализация INsiLookup для сверки КД с БД НСИ (Модуль 1.2)."""

from __future__ import annotations

from pathlib import Path

from app.domain.kd_review.nsi_lookup_port import MaterialRecord, WorkpieceBlankRecord
from app.infrastructure.db.nsi_db import connect


class SqliteNsiLookup:
    def __init__(self, metal_db_path: Path) -> None:
        self._metal_db_path = metal_db_path

    def find_materials(self) -> tuple[MaterialRecord, ...]:
        connection = connect(self._metal_db_path)
        try:
            rows = connection.execute(
                "SELECT grade, gost_standard, density_kg_m3, tensile_strength_mpa, "
                "hardness_hb, machinability_index, hardness_hrc, red_hardness_c, "
                "chemical_composition, heat_treatment, application FROM material"
            ).fetchall()
            return tuple(
                MaterialRecord(
                    grade=row["grade"],
                    gost_standard=row["gost_standard"],
                    density_kg_m3=row["density_kg_m3"],
                    tensile_strength_mpa=row["tensile_strength_mpa"],
                    hardness_hb=row["hardness_hb"],
                    machinability_index=row["machinability_index"],
                    hardness_hrc=row["hardness_hrc"],
                    red_hardness_c=row["red_hardness_c"],
                    chemical_composition=row["chemical_composition"],
                    heat_treatment=row["heat_treatment"],
                    application=row["application"],
                )
                for row in rows
            )
        finally:
            connection.close()

    def find_workpiece_blanks(self) -> tuple[WorkpieceBlankRecord, ...]:
        connection = connect(self._metal_db_path)
        try:
            rows = connection.execute(
                "SELECT designation, diameter_mm, thickness_mm FROM workpiece_blank"
            ).fetchall()
            result = []
            for row in rows:
                gost = self._extract_gost_from_designation(row["designation"])
                result.append(
                    WorkpieceBlankRecord(
                        designation=row["designation"],
                        gost_standard=gost,
                        diameter_mm=row["diameter_mm"],
                        thickness_mm=row["thickness_mm"],
                    )
                )
            return tuple(result)
        finally:
            connection.close()

    def _extract_gost_from_designation(self, designation: str) -> str | None:
        """workpiece_blank в текущей схеме не хранит gost_standard отдельным
        полем — ГОСТ встроен в текст designation ('Круг Ø40 Сталь 45 ГОСТ
        2590-2006'), извлекаем регэкспом, аналогично материалу."""
        import re

        match = re.search(r"ГОСТ\s*[\d.\-]+", designation, re.IGNORECASE)
        return match.group(0) if match else None

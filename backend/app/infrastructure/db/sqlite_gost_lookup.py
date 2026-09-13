"""SQLite-реализация IGostLookup — нормативные требования ГОСТ ЕСКД
для проверки оформления чертежа (Модуль 1.2).

Источник — третья база НСИ (`NsiDatabase.GOST`), собираемая из
`БД НСИ/ГОСТ/` (см. её README). Отдаются только требования,
по которым возможен однозначный автоматический вердикт: ENUM_CHOICE с
заполненным перечнем значений, NUMERIC_LIMIT и графы основной надписи.
Пункты PROCEDURAL остаются в базе для справки технолога, но в проверку
не идут.
"""

from __future__ import annotations

from pathlib import Path

from app.domain.kd_review.gost_lookup_port import (
    GostEnumRequirement,
    GostNumericRequirement,
    GostProceduralRequirement,
    GostTitleBlockField,
)
from app.infrastructure.db.nsi_db import connect


class SqliteGostLookup:
    def __init__(self, gost_db_path: Path) -> None:
        self._gost_db_path = gost_db_path

    def find_enum_requirements(self) -> tuple[GostEnumRequirement, ...]:
        connection = connect(self._gost_db_path)
        try:
            rows = connection.execute(
                "SELECT s.designation, c.clause_number, c.parameter_name, "
                "       c.allowed_values, c.clause_text "
                "FROM gost_clause c "
                "JOIN gost_standard s ON s.id = c.gost_standard_id "
                # allowed_values IS NULL означает, что ряд задан формулой,
                # а не перечнем (напр. «(100n):1» в ГОСТ 2.302 п.4) —
                # такое требование простым сравнением не проверить.
                "WHERE c.requirement_type = 'ENUM_CHOICE' "
                "  AND c.allowed_values IS NOT NULL"
            ).fetchall()
            return tuple(
                GostEnumRequirement(
                    standard_designation=row["designation"],
                    clause_number=row["clause_number"],
                    parameter_name=row["parameter_name"] or "",
                    allowed_values=tuple(
                        v.strip() for v in row["allowed_values"].split(";") if v.strip()
                    ),
                    clause_text=row["clause_text"],
                )
                for row in rows
            )
        finally:
            connection.close()

    def find_numeric_requirements(self) -> tuple[GostNumericRequirement, ...]:
        connection = connect(self._gost_db_path)
        try:
            rows = connection.execute(
                "SELECT s.designation, c.clause_number, c.parameter_name, c.unit, "
                "       c.comparison_op, c.limit_value_min, c.limit_value_max, c.clause_text "
                "FROM gost_clause c "
                "JOIN gost_standard s ON s.id = c.gost_standard_id "
                "WHERE c.requirement_type = 'NUMERIC_LIMIT' "
                "  AND c.comparison_op IS NOT NULL"
            ).fetchall()
            return tuple(
                GostNumericRequirement(
                    standard_designation=row["designation"],
                    clause_number=row["clause_number"],
                    parameter_name=row["parameter_name"] or "",
                    unit=row["unit"],
                    comparison_op=row["comparison_op"],
                    limit_value_min=row["limit_value_min"],
                    limit_value_max=row["limit_value_max"],
                    clause_text=row["clause_text"],
                )
                for row in rows
            )
        finally:
            connection.close()

    def find_title_block_fields(self) -> tuple[GostTitleBlockField, ...]:
        connection = connect(self._gost_db_path)
        try:
            rows = connection.execute(
                "SELECT s.designation, f.field_number, f.field_heading, "
                "       f.content_kind, f.fill_rule, f.required_paper, f.required_electronic "
                "FROM gost_title_block_field f "
                "JOIN gost_standard s ON s.id = f.gost_standard_id"
            ).fetchall()
            return tuple(
                GostTitleBlockField(
                    standard_designation=row["designation"],
                    field_number=row["field_number"],
                    field_heading=row["field_heading"],
                    content_kind=row["content_kind"],
                    fill_rule=row["fill_rule"],
                    required_paper=row["required_paper"],
                    required_electronic=row["required_electronic"],
                )
                for row in rows
            )
        finally:
            connection.close()

    def find_procedural_requirements(self) -> tuple[GostProceduralRequirement, ...]:
        """Структурные правила с явным параметром машинной проверки."""
        connection = connect(self._gost_db_path)
        try:
            rows = connection.execute(
                "SELECT s.designation, c.clause_number, c.parameter_name, c.clause_text "
                "FROM gost_clause c "
                "JOIN gost_standard s ON s.id = c.gost_standard_id "
                "WHERE c.requirement_type = 'PROCEDURAL' "
                "  AND c.parameter_name IS NOT NULL"
            ).fetchall()
            return tuple(
                GostProceduralRequirement(
                    standard_designation=row["designation"],
                    clause_number=row["clause_number"],
                    parameter_name=row["parameter_name"],
                    clause_text=row["clause_text"],
                )
                for row in rows
            )
        finally:
            connection.close()

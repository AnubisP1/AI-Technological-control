"""SQLite-реализация ITypicalRequirementLookup — типовые формулировки ТТ
из таблицы 11 ОСТ 1 02504-84 (справочник metal).

Отдаются ВСЕ формулировки без привязки к типу операции: на этапе оценки
КД техпроцесс ещё не спроектирован, операции неизвестны, и фильтровать
по ним нечем (в отличие от process_planning, где операция уже подобрана).
"""

from __future__ import annotations

from pathlib import Path

from app.domain.kd_review.tt_template_port import TypicalRequirementTemplate
from app.infrastructure.db.nsi_db import connect


class SqliteTypicalRequirementLookup:
    def __init__(self, metal_db_path: Path) -> None:
        self._metal_db_path = metal_db_path

    def find_typical_requirements(self) -> tuple[TypicalRequirementTemplate, ...]:
        connection = connect(self._metal_db_path)
        try:
            rows = connection.execute(
                "SELECT code, formulation_template, reference_standard, notes "
                "FROM machining_requirement_template"
            ).fetchall()
            return tuple(
                TypicalRequirementTemplate(
                    code=row["code"],
                    formulation_template=row["formulation_template"],
                    reference_standard=row["reference_standard"],
                    notes=row["notes"],
                )
                for row in rows
            )
        finally:
            connection.close()

"""Просмотрщик содержимого БД НСИ целиком (Фаза 17, часть 5 — по
запросу пользователя, страница "визуализация БД НСИ") — в отличие от
экрана "Экспертиза НСИ" (сверка КОНКРЕТНОЙ загруженной детали со
справочником), этот сервис отдаёт список таблиц и их содержимое без
привязки к какой-либо детали, для обеих независимых баз (металл/
аддитив, см. dev/docs/ARCHITECTURE.md "База данных").

Имя таблицы нельзя параметризовать через placeholder в SQLite (в
отличие от значений) — подставляется в SQL напрямую, поэтому ВСЕГДА
проверяется по белому списку реальных имён таблиц текущей схемы
(получен через sqlite_master, не от клиента) перед подстановкой.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.infrastructure.db.nsi_db import NsiDatabase, connect

_ROW_LIMIT = 200


@dataclass(frozen=True)
class TableSummary:
    name: str
    row_count: int


@dataclass(frozen=True)
class TableContent:
    name: str
    columns: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]
    total_row_count: int
    truncated: bool


class NsiBrowserService:
    def __init__(self, metal_db_path: Path, additive_db_path: Path) -> None:
        self._db_paths = {
            NsiDatabase.METAL: metal_db_path,
            NsiDatabase.ADDITIVE: additive_db_path,
        }

    def list_tables(self, database: NsiDatabase) -> tuple[TableSummary, ...]:
        connection = connect(self._db_paths[database])
        try:
            table_names = self._real_table_names(connection)
            summaries = []
            for name in table_names:
                count = connection.execute(f'SELECT COUNT(*) AS c FROM "{name}"').fetchone()["c"]
                summaries.append(TableSummary(name=name, row_count=count))
            return tuple(summaries)
        finally:
            connection.close()

    def table_content(self, database: NsiDatabase, table_name: str) -> TableContent | None:
        connection = connect(self._db_paths[database])
        try:
            valid_names = self._real_table_names(connection)
            if table_name not in valid_names:
                return None

            total = connection.execute(f'SELECT COUNT(*) AS c FROM "{table_name}"').fetchone()["c"]
            rows = connection.execute(f'SELECT * FROM "{table_name}" LIMIT {_ROW_LIMIT}').fetchall()
            columns = tuple(rows[0].keys()) if rows else self._columns_of_empty_table(connection, table_name)
            str_rows = tuple(tuple("" if v is None else str(v) for v in row) for row in rows)

            return TableContent(
                name=table_name,
                columns=columns,
                rows=str_rows,
                total_row_count=total,
                truncated=total > _ROW_LIMIT,
            )
        finally:
            connection.close()

    def _real_table_names(self, connection) -> set[str]:
        rows = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
        return {row["name"] for row in rows}

    def _columns_of_empty_table(self, connection, table_name: str) -> tuple[str, ...]:
        cursor = connection.execute(f'SELECT * FROM "{table_name}" LIMIT 0')
        return tuple(col[0] for col in cursor.description)

"""Загрузка НСИ (нормативно-справочной информации) в локальный SQLite.

Схемы адаптированы из PostgreSQL-оригиналов в ../../../../../../БД НСИ/
и ../../../../../../БД НСИ Аддитив/ (см. dev/docs/ARCHITECTURE.md,
раздел "База данных", и dev/PLAN.md Фаза 1). Два независимых набора
таблиц — металлообработка и аддитивные технологии — не связаны FK
между собой по проектному решению оригинальных схем.
"""

from __future__ import annotations

import sqlite3
from enum import Enum
from pathlib import Path

SCHEMA_ROOT = Path(__file__).resolve().parent / "schema_sqlite"


class NsiDatabase(str, Enum):
    METAL = "metal"
    ADDITIVE = "additive"
    # Нормативные требования ГОСТ ЕСКД к оформлению КД. Отдельная, ТРЕТЬЯ
    # база: металл и аддитив — справочники ресурсов предприятия и не
    # связаны между собой по замыслу оригинальных схем, а ГОСТ на
    # оформление чертежа применим к обеим ветвям одинаково, поэтому
    # дублировать его в двух схемах было бы неверно (см. БД НСИ/ГОСТ/README.md).
    GOST = "gost"


# Порядок seed-файлов важен и не совпадает с алфавитным: seed_data.sql
# создаёт базовые справочники (printer_type, am_part и т.д.), от которых
# зависят строки в seed_application_rules.sql (правила подбора по классу
# детали ссылаются на printer_type_id, заведённый в seed_data.sql).
_SEED_FILE_ORDER: dict[NsiDatabase, list[str]] = {
    NsiDatabase.METAL: [
        "seed_data.sql",
        "seed_typical_technical_requirements.sql",
        "seed_cutting_modes.sql",
    ],
    NsiDatabase.ADDITIVE: [
        "seed_data.sql",
        "seed_application_rules.sql",
        "seed_print_quality_standards.sql",
        "seed_print_speed_reference.sql",
    ],
    # Сначала сами стандарты, затем пункты по каждому, и последним —
    # связи между пунктами РАЗНЫХ стандартов: такая связь ссылается на
    # целевой пункт по id, и если вставить её раньше, чем размечен
    # целевой стандарт, INSERT ... SELECT молча вставит 0 строк без
    # ошибки (ровно эта ошибка уже была допущена при наполнении базы,
    # см. шапку zz_seed_cross_references.sql).
    NsiDatabase.GOST: [
        "seed_gost_standards.sql",
        "seed_gost_2104_title_block.sql",
        "seed_gost_2109_clauses.sql",
        "seed_gost_2302_clauses.sql",
        "seed_gost_2305_clauses.sql",
        "seed_gost_2307_clauses.sql",
        "seed_gost_2316_clauses.sql",
        "seed_gost_25142_clauses.sql",
        # Сортамент материала (не ЕСКД): допустимые размеры плит, с которыми
        # сверяется заготовка из основной надписи чертежа.
        "seed_gost_17232_clauses.sql",
        "zz_seed_cross_references.sql",
    ],
}


def _schema_files_in_order(directory: Path) -> list[Path]:
    return sorted(directory.glob("*.sql"), key=lambda p: p.name)


def _seed_files_in_order(database: NsiDatabase, directory: Path) -> list[Path]:
    return [directory / name for name in _SEED_FILE_ORDER[database]]


def build_database(database: NsiDatabase, db_path: Path, *, with_seed: bool = True) -> None:
    """Создаёт SQLite-файл db_path и заполняет его схемой (и опционально seed-данными).

    db_path.parent создаётся при необходимости (кроссплатформенно через pathlib).
    Существующий файл по этому пути перезаписывается.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()

    root = SCHEMA_ROOT / database.value
    connection = sqlite3.connect(db_path)
    try:
        connection.execute("PRAGMA foreign_keys = ON;")
        for sql_file in _schema_files_in_order(root / "schema"):
            connection.executescript(sql_file.read_text(encoding="utf-8"))
        if with_seed:
            for sql_file in _seed_files_in_order(database, root / "seed"):
                connection.executescript(sql_file.read_text(encoding="utf-8"))
        connection.commit()
    finally:
        connection.close()


def connect(db_path: Path) -> sqlite3.Connection:
    """Открывает соединение с включённой проверкой внешних ключей."""
    connection = sqlite3.connect(db_path)
    connection.execute("PRAGMA foreign_keys = ON;")
    connection.row_factory = sqlite3.Row
    return connection

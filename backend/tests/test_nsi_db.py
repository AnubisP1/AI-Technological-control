from pathlib import Path

import pytest

from app.infrastructure.db.nsi_db import NsiDatabase, build_database, connect


@pytest.fixture
def metal_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "metal.sqlite"
    build_database(NsiDatabase.METAL, db_path)
    return db_path


@pytest.fixture
def additive_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "additive.sqlite"
    build_database(NsiDatabase.ADDITIVE, db_path)
    return db_path


def test_metal_schema_and_seed_load_without_errors(metal_db: Path):
    connection = connect(metal_db)
    try:
        tables = {
            row["name"]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        assert {"equipment_type", "process", "operation", "transition", "document_template"} <= tables
    finally:
        connection.close()


def test_metal_compatibility_matrix_drives_dropdown_filtering(metal_db: Path):
    """Ключевая таблица equipment_type_tooling_type должна давать непустой
    результат для реального типа станка из seed-данных (id=3, токарно-винторезный)."""
    connection = connect(metal_db)
    try:
        rows = connection.execute(
            "SELECT tooling_type_id FROM equipment_type_tooling_type WHERE equipment_type_id = 3"
        ).fetchall()
        assert len(rows) > 0
    finally:
        connection.close()


def test_metal_workpiece_part_fk_resolves_despite_deferred_creation_order(metal_db: Path):
    """workpiece.part_id ссылается на part, которая создаётся в более позднем
    файле (06_process.sql) — оригинальная PostgreSQL-схема замыкала эту связь
    через ALTER TABLE ADD CONSTRAINT; SQLite-версия объявляет FK сразу
    в CREATE TABLE workpiece (04). Проверяем, что вставка реально проходит
    проверку внешнего ключа (PRAGMA foreign_keys=ON)."""
    connection = connect(metal_db)
    try:
        connection.execute(
            "INSERT INTO workpiece (workpiece_blank_id, part_id, cut_length_mm) VALUES (1, 1, 120)"
        )
        connection.commit()
        row = connection.execute("SELECT part_id FROM workpiece WHERE cut_length_mm = 120").fetchone()
        assert row["part_id"] == 1

        with pytest.raises(Exception):
            connection.execute(
                "INSERT INTO workpiece (workpiece_blank_id, part_id, cut_length_mm) VALUES (1, 9999, 50)"
            )
            connection.commit()
    finally:
        connection.close()


def test_additive_schema_and_seed_load_without_errors(additive_db: Path):
    connection = connect(additive_db)
    try:
        tables = {
            row["name"]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        assert {"am_technology", "printer_model", "print_process", "application_material_recommendation"} <= tables
    finally:
        connection.close()


def test_additive_am_part_application_class_column_added_via_alter(additive_db: Path):
    """08_application_rules.sql добавляет part_application_class_id в am_part
    через ALTER TABLE ADD COLUMN — проверяем, что колонка реально появилась
    и на неё можно сослаться."""
    connection = connect(additive_db)
    try:
        columns = {row["name"] for row in connection.execute("PRAGMA table_info(am_part)")}
        assert "part_application_class_id" in columns

        connection.execute(
            "UPDATE am_part SET part_application_class_id = 1 WHERE id = 1"
        )
        connection.commit()
        row = connection.execute(
            "SELECT part_application_class_id FROM am_part WHERE id = 1"
        ).fetchone()
        assert row["part_application_class_id"] == 1
    finally:
        connection.close()


def test_additive_application_material_recommendation_has_seeded_rows(additive_db: Path):
    connection = connect(additive_db)
    try:
        count = connection.execute(
            "SELECT COUNT(*) AS c FROM application_material_recommendation"
        ).fetchone()["c"]
        assert count > 0
    finally:
        connection.close()


def test_build_database_without_seed_creates_empty_tables(tmp_path: Path):
    db_path = tmp_path / "metal_no_seed.sqlite"
    build_database(NsiDatabase.METAL, db_path, with_seed=False)
    connection = connect(db_path)
    try:
        count = connection.execute("SELECT COUNT(*) AS c FROM equipment_type").fetchone()["c"]
        assert count == 0
    finally:
        connection.close()

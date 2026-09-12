from pathlib import Path

from app.infrastructure.db.nsi_db import NsiDatabase, build_database
from app.services.nsi_browser_service import NsiBrowserService


def _service(tmp_path: Path) -> NsiBrowserService:
    metal_path = tmp_path / "metal.sqlite"
    additive_path = tmp_path / "additive.sqlite"
    build_database(NsiDatabase.METAL, metal_path)
    build_database(NsiDatabase.ADDITIVE, additive_path)
    return NsiBrowserService(metal_path, additive_path)


def test_list_tables_returns_real_tables_with_row_counts(tmp_path: Path):
    service = _service(tmp_path)
    tables = service.list_tables(NsiDatabase.METAL)

    names = {t.name for t in tables}
    assert "material" in names
    assert "equipment_model" in names
    assert "sqlite_sequence" not in names  # служебная таблица SQLite, не часть НСИ

    material_table = next(t for t in tables if t.name == "material")
    # 21 марка сталей/чугуна (2026-08-04) + 3 алюминиевые марки серии МВАУ
    # (Д16, АД31, АМг2), добавленные вместе с плоским сортаментом.
    assert material_table.row_count == 24


def test_table_content_returns_real_seed_rows(tmp_path: Path):
    service = _service(tmp_path)
    content = service.table_content(NsiDatabase.METAL, "material")

    assert content is not None
    assert "grade" in content.columns
    assert content.total_row_count == 24
    assert content.truncated is False
    grades = [row[content.columns.index("grade")] for row in content.rows]
    assert "Сталь 45" in grades
    assert "12ХН3А" in grades
    assert "Р18" in grades
    assert "65Г" in grades


def test_table_content_returns_none_for_unknown_table(tmp_path: Path):
    """Регрессия/безопасность: имя таблицы нельзя параметризовать через
    SQL placeholder в SQLite — обязана проверяться по белому списку
    реальных имён, не подставляться напрямую от клиента."""
    service = _service(tmp_path)
    content = service.table_content(NsiDatabase.METAL, "material'; DROP TABLE material;--")
    assert content is None


def test_list_tables_works_for_additive_database(tmp_path: Path):
    service = _service(tmp_path)
    tables = service.list_tables(NsiDatabase.ADDITIVE)
    names = {t.name for t in tables}
    assert "am_material" in names
    assert "printer_model" in names

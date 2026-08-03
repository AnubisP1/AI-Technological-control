from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_list_nsi_tables_endpoint_returns_metal_tables():
    response = client.get("/nsi/metal/tables")
    assert response.status_code == 200
    body = response.json()
    names = {t["name"] for t in body}
    assert "material" in names
    assert "equipment_model" in names


def test_list_nsi_tables_endpoint_returns_404_for_unknown_database():
    response = client.get("/nsi/unknown/tables")
    assert response.status_code == 404


def test_get_nsi_table_content_endpoint_returns_rows():
    response = client.get("/nsi/metal/tables/material")
    assert response.status_code == 200
    body = response.json()
    assert "grade" in body["columns"]
    assert body["total_row_count"] > 0
    assert body["rows"]


def test_get_nsi_table_content_endpoint_returns_404_for_unknown_table():
    response = client.get("/nsi/metal/tables/not_a_real_table")
    assert response.status_code == 404


def test_get_nsi_table_content_endpoint_rejects_sql_injection_attempt():
    response = client.get("/nsi/metal/tables/material'; DROP TABLE material;--")
    assert response.status_code == 404

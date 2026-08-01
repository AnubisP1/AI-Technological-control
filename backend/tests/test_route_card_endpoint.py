from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

FIXTURES_ROOT = Path(__file__).resolve().parents[3] / "КД для тестов" / "Детали из металла"
VAL_PDF = FIXTURES_ROOT / "1. Тестовая деталь металл" / "К200-150-400ENERAL.20 - Вал.pdf"

client = TestClient(app)


def _require(path: Path) -> Path:
    if not path.exists():
        pytest.skip(f"fixture недоступен в этом окружении: {path}")
    return path


def test_route_card_endpoint_generates_card_with_columns_from_template():
    drawing_path = _require(VAL_PDF)

    with drawing_path.open("rb") as drawing_file:
        response = client.post(
            "/kd/route-card",
            files={"drawing": (drawing_path.name, drawing_file, "application/pdf")},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["part_name"] == "Вал"
    assert body["gost_form"] == "ГОСТ 3.1118-82, форма 1"
    assert "№ операции" in body["columns"]
    assert len(body["rows"]) > 0
    # Каждая строка должна иметь то же число значений, что и столбцов.
    for row in body["rows"]:
        assert len(row) == len(body["columns"])

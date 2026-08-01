from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

METAL_FIXTURES_ROOT = Path(__file__).resolve().parents[3] / "КД для тестов" / "Детали из металла"
VAL_PDF = METAL_FIXTURES_ROOT / "1. Тестовая деталь металл" / "К200-150-400ENERAL.20 - Вал.pdf"

PLASTIC_FIXTURES_ROOT = Path(__file__).resolve().parents[3] / "КД для тестов" / "Пластиковые детали"
PLASTIC_STEP = PLASTIC_FIXTURES_ROOT / "1. Тестовая деталь пластик" / "SQUID RUS 2_крышка 2.STEP"

client = TestClient(app)


def _require(path: Path) -> Path:
    if not path.exists():
        pytest.skip(f"fixture недоступен в этом окружении: {path}")
    return path


def test_approval_approve_without_comment():
    response = client.post("/manufacturing/approval", params={"decision": "approved"})

    assert response.status_code == 200
    body = response.json()
    assert body["can_start_simulation"] is True
    assert body["comment"] is None


def test_approval_reject_with_comment():
    response = client.post(
        "/manufacturing/approval",
        params={"decision": "rejected", "comment": "Не указан разряд оператора"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["can_start_simulation"] is False
    assert body["comment"] == "Не указан разряд оператора"


def test_approval_reject_without_comment_returns_422():
    response = client.post("/manufacturing/approval", params={"decision": "rejected"})

    assert response.status_code == 422


def test_approval_unknown_decision_returns_422():
    response = client.post("/manufacturing/approval", params={"decision": "maybe"})

    assert response.status_code == 422


def test_simulate_metal_endpoint_returns_plan_with_total_15_seconds():
    drawing_path = _require(VAL_PDF)

    with drawing_path.open("rb") as drawing_file:
        response = client.post(
            "/manufacturing/simulate/metal",
            files={"drawing": (drawing_path.name, drawing_file, "application/pdf")},
        )

    assert response.status_code == 200
    body = response.json()
    plan = body["plan"]
    assert plan["material_kind"] == "metal"
    assert plan["total_seconds"] == 15
    assert len(plan["operations"]) > 0
    for operation in plan["operations"]:
        assert "machine_icon" in operation
        assert "program_lines" in operation


def test_simulate_print_endpoint_returns_plan_with_printer_and_postprocessing():
    step_path = _require(PLASTIC_STEP)

    with step_path.open("rb") as step_file:
        response = client.post(
            "/manufacturing/simulate/print",
            params={"am_technology_code": "SLA", "material_group_code": "RESIN_TOUGH"},
            files={"step_model": (step_path.name, step_file, "application/octet-stream")},
        )

    assert response.status_code == 200
    body = response.json()
    plan = body["plan"]
    assert plan["material_kind"] == "plastic"
    assert plan["total_seconds"] == 15
    assert plan["operations"][0]["machine_icon"] == "resin_printer"
    assert len(plan["operations"]) > 1

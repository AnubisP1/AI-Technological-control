from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

FIXTURES_ROOT = Path(__file__).resolve().parents[3] / "КД для тестов" / "Пластиковые детали"
PLASTIC_STEP = FIXTURES_ROOT / "1. Тестовая деталь пластик" / "SQUID RUS 2_крышка 2.STEP"

client = TestClient(app)


def _require(path: Path) -> Path:
    if not path.exists():
        pytest.skip(f"fixture недоступен в этом окружении: {path}")
    return path


def test_print_route_card_endpoint_generates_process_and_postprocessing_cards():
    """Реальный fixture пластиковой детали (крышка): на вход только STEP,
    без чертежа — материал/технология указываются явно, как того требует
    сценарий 'для пластиковых изделий' из Техническое задание.md."""
    step_path = _require(PLASTIC_STEP)

    with step_path.open("rb") as step_file:
        response = client.post(
            "/print/route-card",
            params={"am_technology_code": "SLA", "material_group_code": "RESIN_TOUGH"},
            files={"step_model": (step_path.name, step_file, "application/octet-stream")},
        )

    assert response.status_code == 200
    body = response.json()
    assert "Технология" in body["process_card"]["columns"]
    assert body["process_card"]["row"][0] == "SLA"
    assert len(body["postprocessing_card"]["rows"]) > 0
    assert body["warnings"] == []
    # Допуски/шероховатость по технологии (inner.su, am_technology_tolerance)
    # должны попадать в карту техпроцесса печати.
    quality_standard = body["process_card"]["quality_standard"]
    assert quality_standard is not None
    assert quality_standard["tolerance_mm"].startswith("±")
    assert "inner.su" in quality_standard["source_note"]
    # material_print_profile (Фаза 20, экспертиза НСИ по пластику) —
    # температуры печати смолы не заполнены (не FDM-филамент), но марка
    # и требования к хранению/камере должны прийти.
    profile = body["material_print_profile"]
    assert profile is not None
    assert profile["trade_name"] == "Formlabs Tough 2000 Resin"
    assert profile["print_temp_min_c"] is None


def test_print_route_card_endpoint_reports_warning_for_unknown_material():
    step_path = _require(PLASTIC_STEP)

    with step_path.open("rb") as step_file:
        response = client.post(
            "/print/route-card",
            params={"am_technology_code": "FDM", "material_group_code": "UNOBTAINIUM"},
            files={"step_model": (step_path.name, step_file, "application/octet-stream")},
        )

    assert response.status_code == 200
    body = response.json()
    assert len(body["warnings"]) == 1

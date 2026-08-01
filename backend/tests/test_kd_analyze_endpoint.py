from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

FIXTURES_ROOT = Path(__file__).resolve().parents[3] / "КД для тестов" / "Детали из металла"
VAL_DIR = FIXTURES_ROOT / "1. Тестовая деталь металл"
VAL_PDF = VAL_DIR / "К200-150-400ENERAL.20 - Вал.pdf"
VAL_STEP = VAL_DIR / "3D_К200-150-400 - Вал.stp"

client = TestClient(app)


def _require(path: Path) -> Path:
    if not path.exists():
        pytest.skip(f"fixture недоступен в этом окружении: {path}")
    return path


def test_analyze_kd_with_both_drawing_and_step():
    drawing_path = _require(VAL_PDF)
    step_path = _require(VAL_STEP)

    with drawing_path.open("rb") as drawing_file, step_path.open("rb") as step_file:
        response = client.post(
            "/kd/analyze",
            files={
                "drawing": (drawing_path.name, drawing_file, "application/pdf"),
                "step_model": (step_path.name, step_file, "application/octet-stream"),
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["is_complete"] is True
    assert body["drawing"]["title_block"]["designation"] == "К200-150-400ENERAL.20"
    assert body["drawing"]["title_block"]["part_name"] == "Вал"
    assert len(body["drawing"]["technical_requirements"]) == 7
    assert body["view_detection"]["method"] == "vector_clustering"
    assert body["view_detection"]["view_count"] > 0
    assert body["step_model"]["face_count"] > 0
    assert body["step_model"]["bounding_box"]["length_x"] == pytest.approx(707.488, abs=0.5)


def test_analyze_kd_with_only_step_model_for_plastic_parts():
    """По ТЗ для пластиковых изделий на вход подаётся только STEP-модель
    (без чертежа/спецификации) — сценарий должен работать без drawing."""
    step_path = _require(VAL_STEP)

    with step_path.open("rb") as step_file:
        response = client.post(
            "/kd/analyze",
            files={"step_model": (step_path.name, step_file, "application/octet-stream")},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["is_complete"] is False
    assert body["drawing"] is None
    assert body["step_model"] is not None


def test_analyze_kd_with_no_files_returns_empty_result():
    response = client.post("/kd/analyze")
    assert response.status_code == 200
    body = response.json()
    assert body == {
        "is_complete": False,
        "drawing": None,
        "view_detection": None,
        "step_model": None,
    }

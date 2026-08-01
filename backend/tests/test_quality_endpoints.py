from pathlib import Path

import cv2
import pytest
from fastapi.testclient import TestClient

from app.main import app

METAL_FIXTURES_ROOT = Path(__file__).resolve().parents[3] / "КД для тестов" / "Детали из металла"
VAL_PDF = METAL_FIXTURES_ROOT / "1. Тестовая деталь металл" / "К200-150-400ENERAL.20 - Вал.pdf"

PLASTIC_FIXTURES_ROOT = Path(__file__).resolve().parents[3] / "КД для тестов" / "Пластиковые детали" / "1. Тестовая деталь пластик"
PLASTIC_STEP = PLASTIC_FIXTURES_ROOT / "SQUID RUS 2_крышка 2.STEP"
PHOTO_A = PLASTIC_FIXTURES_ROOT / "7a6046ea-69b2-44f2-ac83-3f9c0ba8a923.jpeg"
PHOTO_B = PLASTIC_FIXTURES_ROOT / "fd46d227-602c-4b9b-bf28-de9a04a490a1.jpeg"

client = TestClient(app)


def _require(path: Path) -> Path:
    if not path.exists():
        pytest.skip(f"fixture недоступен в этом окружении: {path}")
    return path


def test_assess_quality_print_ok_branch_returns_serial_production_plan(tmp_path):
    step_path = _require(PLASTIC_STEP)
    reference = _require(PHOTO_A)
    actual = _require(PHOTO_B)

    with step_path.open("rb") as step_file, reference.open("rb") as ref_file, actual.open(
        "rb"
    ) as actual_file:
        response = client.post(
            "/quality/assess/print",
            params={"am_technology_code": "SLA", "material_group_code": "RESIN_TOUGH"},
            files={
                "step_model": (step_path.name, step_file, "application/octet-stream"),
                "reference_photo": (reference.name, ref_file, "image/jpeg"),
                "actual_photo": (actual.name, actual_file, "image/jpeg"),
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["verdict"] == "ok"
    assert body["serial_production_plan"] is not None
    assert body["serial_production_plan"]["is_demonstration_estimate"] is True
    assert len(body["optimization_suggestions"]) > 0
    assert body["remediation_recommendations"] == []


def test_assess_quality_print_defective_branch_returns_remediation(tmp_path):
    step_path = _require(PLASTIC_STEP)
    reference = _require(PHOTO_B)

    image = cv2.imread(str(_require(PHOTO_A)))
    height, width = image.shape[:2]
    cv2.rectangle(
        image,
        (int(width * 0.32), int(height * 0.35)),
        (int(width * 0.72), int(height * 0.65)),
        (170, 170, 165),
        -1,
    )
    defective_photo_path = tmp_path / "defective.jpg"
    cv2.imwrite(str(defective_photo_path), image)

    with step_path.open("rb") as step_file, reference.open("rb") as ref_file, defective_photo_path.open(
        "rb"
    ) as actual_file:
        response = client.post(
            "/quality/assess/print",
            params={"am_technology_code": "SLA", "material_group_code": "RESIN_TOUGH"},
            files={
                "step_model": (step_path.name, step_file, "application/octet-stream"),
                "reference_photo": (reference.name, ref_file, "image/jpeg"),
                "actual_photo": (defective_photo_path.name, actual_file, "image/jpeg"),
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["verdict"] == "defective"
    assert body["serial_production_plan"] is None
    assert len(body["remediation_recommendations"]) > 0


def test_assess_quality_metal_endpoint_runs_end_to_end(tmp_path):
    drawing_path = _require(VAL_PDF)
    reference = _require(PHOTO_A)
    actual = _require(PHOTO_B)

    with drawing_path.open("rb") as drawing_file, reference.open("rb") as ref_file, actual.open(
        "rb"
    ) as actual_file:
        response = client.post(
            "/quality/assess/metal",
            files={
                "drawing": (drawing_path.name, drawing_file, "application/pdf"),
                "reference_photo": (reference.name, ref_file, "image/jpeg"),
                "actual_photo": (actual.name, actual_file, "image/jpeg"),
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["verdict"] in {"ok", "defective", "inconclusive"}
    assert "similarity_score" in body

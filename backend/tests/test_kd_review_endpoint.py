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


def test_review_endpoint_returns_material_and_blank_checks():
    drawing_path = _require(VAL_PDF)

    with drawing_path.open("rb") as drawing_file:
        response = client.post(
            "/kd/review",
            files={"drawing": (drawing_path.name, drawing_file, "application/pdf")},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["material_check"]["status"] == "matched"
    assert body["blank_check"]["status"] == "partial_match"
    assert len(body["technical_requirement_checks"]) == 7
    assert isinstance(body["findings"], list)
    assert body["has_blocking_findings"] is False
    # generated_by зависит от окружения (llm, если в .env настроен
    # реальный LLM-провайдер — Polza.ai/локальный Qwen, Фаза 18, часть 2;
    # иначе template) — оба пути обязаны дать непустой текст резюме.
    assert body["summary"]["generated_by"] in ("template", "llm")
    assert body["summary"]["text"]

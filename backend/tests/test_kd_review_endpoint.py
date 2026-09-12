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


def test_review_endpoint_returns_gost_checks():
    """Фаза 23: проверки оформления по ГОСТ ЕСКД (база `БД НСИ/ГОСТ/`)
    выполняются в том же запросе, что и сверка с НСИ, и по одному
    чертежу — без 3D-модели."""
    drawing_path = _require(VAL_PDF)

    with drawing_path.open("rb") as drawing_file:
        response = client.post(
            "/kd/review",
            files={"drawing": (drawing_path.name, drawing_file, "application/pdf")},
        )

    assert response.status_code == 200
    gost_checks = response.json()["gost_checks"]
    assert gost_checks, "раздел проверок ГОСТ не должен быть пустым при подключённой базе"

    allowed_statuses = {"passed", "violated", "needs_review", "not_applicable"}
    for check in gost_checks:
        assert check["status"] in allowed_statuses
        assert check["standard_designation"].startswith("ГОСТ")
        assert check["clause_number"]
        assert check["parameter_name"]

    checked = {(c["standard_designation"], c["clause_number"]) for c in gost_checks}
    # Масштаб «1:2» из основной надписи этого чертежа сверяется с рядом
    # ГОСТ 2.302 — требование берётся из базы, не зашито в коде.
    assert any(std.startswith("ГОСТ 2.302") for std, _ in checked)
    # Графы основной надписи — из таблицы 1 ГОСТ Р 2.104.
    assert any(clause.startswith("графа") for _, clause in checked)

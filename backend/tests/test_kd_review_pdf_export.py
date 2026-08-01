from pathlib import Path

import fitz
import pytest
from fastapi.testclient import TestClient

from app.infrastructure.cad.pdf_drawing_parser import PdfDrawingParser
from app.infrastructure.db.nsi_db import NsiDatabase, build_database
from app.infrastructure.db.sqlite_nsi_lookup import SqliteNsiLookup
from app.main import app
from app.services.kd_review_pdf_export import generate_kd_review_pdf
from app.services.kd_review_service import KdReviewService

FIXTURES_ROOT = Path(__file__).resolve().parents[3] / "КД для тестов" / "Детали из металла"
VAL_PDF = FIXTURES_ROOT / "1. Тестовая деталь металл" / "К200-150-400ENERAL.20 - Вал.pdf"

client = TestClient(app)


def _require(path: Path) -> Path:
    if not path.exists():
        pytest.skip(f"fixture недоступен в этом окружении: {path}")
    return path


def test_generate_kd_review_pdf_produces_valid_pdf_with_expected_text(tmp_path):
    drawing_path = _require(VAL_PDF)
    drawing_model = PdfDrawingParser().parse(drawing_path)
    metal_db_path = tmp_path / "metal.sqlite"
    build_database(NsiDatabase.METAL, metal_db_path)

    service = KdReviewService(nsi_lookup=SqliteNsiLookup(metal_db_path))
    report = service.review(drawing_model)

    pdf_bytes = generate_kd_review_pdf(report, part_name="Вал")

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        full_text = "".join(page.get_text() for page in doc)
    finally:
        doc.close()

    assert "Отчёт об оценке конструкторской документации" in full_text
    assert "Дерево проверок" in full_text
    assert "Резюме" in full_text


def test_review_pdf_endpoint_returns_pdf_content_type():
    drawing_path = _require(VAL_PDF)

    with drawing_path.open("rb") as drawing_file:
        response = client.post(
            "/kd/review/pdf",
            files={"drawing": (drawing_path.name, drawing_file, "application/pdf")},
        )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")

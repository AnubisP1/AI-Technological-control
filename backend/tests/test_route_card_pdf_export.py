from pathlib import Path

import fitz
import pytest
from fastapi.testclient import TestClient

from app.infrastructure.db.nsi_db import NsiDatabase, build_database
from app.infrastructure.db.sqlite_process_planning_lookup import SqliteProcessPlanningLookup
from app.main import app
from app.services.process_planning_service import ProcessPlanningService
from app.services.route_card_generator import RouteCardGenerator
from app.services.route_card_pdf_export import generate_route_card_pdf

FIXTURES_ROOT = Path(__file__).resolve().parents[3] / "КД для тестов" / "Детали из металла"
VAL_PDF = FIXTURES_ROOT / "1. Тестовая деталь металл" / "К200-150-400ENERAL.20 - Вал.pdf"

client = TestClient(app)


def _require(path: Path) -> Path:
    if not path.exists():
        pytest.skip(f"fixture недоступен в этом окружении: {path}")
    return path


def test_generate_route_card_pdf_produces_valid_pdf_with_real_grid(tmp_path: Path):
    db_path = tmp_path / "metal.sqlite"
    build_database(NsiDatabase.METAL, db_path)
    service = ProcessPlanningService(SqliteProcessPlanningLookup(db_path))
    result = service.plan(
        part_name="Вал",
        material_grade="45 ГОСТ 1050-2013",
        blank_designation="Круг 67 ГОСТ 2590-2006",
    )
    columns = (
        "№ операции",
        "Код/наименование операции",
        "Цех",
        "Уч.",
        "РМ",
        "Профессия/разряд",
        "Оборудование",
        "Тпз",
        "Тшт",
    )
    route_card = RouteCardGenerator().generate(result, columns=columns, gost_form="1")

    pdf_bytes = generate_route_card_pdf(route_card, doc_number="МК.01.00.000")

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        full_text = "".join(page.get_text() for page in doc)
    finally:
        doc.close()

    assert pdf_bytes.startswith(b"%PDF")
    assert "ГОСТ 3.1118-82" in full_text
    assert "Маршрутная карта" in full_text
    assert "TURN_ROUGH" in full_text


def test_route_card_pdf_endpoint_returns_pdf_content_type():
    drawing_path = _require(VAL_PDF)

    with drawing_path.open("rb") as drawing_file:
        response = client.post(
            "/kd/route-card/pdf",
            files={"drawing": (drawing_path.name, drawing_file, "application/pdf")},
        )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")

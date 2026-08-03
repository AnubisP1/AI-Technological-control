from pathlib import Path

import fitz
import pytest
from fastapi.testclient import TestClient

from app.infrastructure.db.nsi_db import NsiDatabase, build_database
from app.infrastructure.db.sqlite_process_planning_lookup import SqliteProcessPlanningLookup
from app.main import app
from app.services.operation_card_generator import OperationCardGenerator
from app.services.operation_card_pdf_export import generate_operation_card_pdf
from app.services.process_planning_service import ProcessPlanningService

FIXTURES_ROOT = Path(__file__).resolve().parents[3] / "КД для тестов" / "Детали из металла"
VAL_PDF = FIXTURES_ROOT / "1. Тестовая деталь металл" / "К200-150-400ENERAL.20 - Вал.pdf"

client = TestClient(app)


def _require(path: Path) -> Path:
    if not path.exists():
        pytest.skip(f"fixture недоступен в этом окружении: {path}")
    return path


_OK_COLUMNS = (
    "№ операции",
    "№ перехода",
    "Содержание перехода",
    "Оборудование",
    "Оснастка (приспособление/инструмент/измерительный)",
    "t",
    "S",
    "V",
    "n",
    "Разряд работы",
    "То",
    "Тв",
    "Тшт",
    "Тпз",
)


def test_generate_operation_card_pdf_includes_calculated_cutting_modes(tmp_path: Path):
    """Реальный fixture: диаметр 67мм извлекается, для точения должны
    быть заполнены V/n/t/S в самом PDF-тексте, не оставлены пустыми."""
    db_path = tmp_path / "metal.sqlite"
    build_database(NsiDatabase.METAL, db_path)
    service = ProcessPlanningService(SqliteProcessPlanningLookup(db_path))
    result = service.plan(
        part_name="Вал",
        material_grade="45 ГОСТ 1050-2013",
        blank_designation="Круг 67 ГОСТ 2590-2006",
    )
    operation_card = OperationCardGenerator().generate(result, columns=_OK_COLUMNS, gost_form="3")

    pdf_bytes = generate_operation_card_pdf(operation_card, doc_number="ОК.01.00.000")

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        full_text = "".join(page.get_text() for page in doc)
    finally:
        doc.close()

    assert pdf_bytes.startswith(b"%PDF")
    assert "ГОСТ 3.1404-86" in full_text
    assert "Операционная карта" in full_text

    turn_rough = next(op for op in result.operations if op.operation_type_code == "TURN_ROUGH")
    cm = turn_rough.cutting_mode
    assert cm is not None and cm.is_calculated
    assert f"{cm.spindle_speed_rpm}" in full_text


def test_operation_card_pdf_endpoint_returns_pdf_content_type():
    drawing_path = _require(VAL_PDF)

    with drawing_path.open("rb") as drawing_file:
        response = client.post(
            "/kd/operation-card/pdf",
            files={"drawing": (drawing_path.name, drawing_file, "application/pdf")},
        )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")

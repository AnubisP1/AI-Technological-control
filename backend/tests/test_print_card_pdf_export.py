from pathlib import Path

import fitz
import pytest
from fastapi.testclient import TestClient

from app.domain.process_planning.print_card_model import PostprocessingCard, PrintCardRow, PrintProcessCard
from app.main import app
from app.services.print_card_pdf_export import generate_print_card_pdf

FIXTURES_ROOT = Path(__file__).resolve().parents[3] / "КД для тестов" / "Пластиковые детали"
PLASTIC_STEP = FIXTURES_ROOT / "1. Тестовая деталь пластик" / "SQUID RUS 2_крышка 2.STEP"

client = TestClient(app)


def _require(path: Path) -> Path:
    if not path.exists():
        pytest.skip(f"fixture недоступен в этом окружении: {path}")
    return path


def test_generate_print_card_pdf_produces_valid_pdf_with_grid():
    columns = ("Технология", "Принтер", "Материал", "Высота слоя", "Заполнение", "Время печати", "Расход материала")
    row = PrintCardRow(values=("FDM", "Prusa MK4", "PETG", "0.2 мм", "", "2199.3 мин", "410.5 г"))
    process_card = PrintProcessCard(
        part_name="Крышка SQUID RUS 2",
        columns=columns,
        row=row,
        quality_standard=None,
        print_estimate_note="Оценка по 25% объёма bounding box.",
    )
    pp_columns = ("№ шага", "Операция", "Оборудование", "Длительность", "Температура", "Влияние на точность/шероховатость")
    pp_card = PostprocessingCard(
        columns=pp_columns,
        rows=(PrintCardRow(values=("1", "Удаление поддержек", "", "", "", "")),),
    )

    pdf_bytes = generate_print_card_pdf(process_card, pp_card)

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        full_text = "".join(page.get_text() for page in doc)
    finally:
        doc.close()

    assert pdf_bytes.startswith(b"%PDF")
    assert "Карта техпроцесса печати" in full_text
    assert "FDM" in full_text
    assert "Карта постобработки" in full_text


def test_print_route_card_pdf_endpoint_returns_pdf_content_type():
    step_path = _require(PLASTIC_STEP)

    with step_path.open("rb") as step_file:
        response = client.post(
            "/print/route-card/pdf",
            params={"am_technology_code": "FDM", "material_group_code": "PETG"},
            files={"step_model": (step_path.name, step_file, "application/octet-stream")},
        )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")

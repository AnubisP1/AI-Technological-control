from pathlib import Path

import pytest

from app.infrastructure.cad.pdf_drawing_parser import PdfDrawingParser

FIXTURES_ROOT = Path(__file__).resolve().parents[3] / "КД для тестов" / "Детали из металла"

VAL_PDF = FIXTURES_ROOT / "1. Тестовая деталь металл" / "К200-150-400ENERAL.20 - Вал.pdf"
GEAR_PDF = (
    FIXTURES_ROOT
    / "2. Тестовая деталь металл"
    / "Шестерня от конической передачи с круговым зубом редуктора TS 030411.04.950 _ KPP-5002-11.10.2024.pdf"
)


def _require(path: Path) -> Path:
    if not path.exists():
        pytest.skip(f"fixture недоступен в этом окружении: {path}")
    return path


def test_val_drawing_title_block_fully_extracted():
    parser = PdfDrawingParser()
    model = parser.parse(_require(VAL_PDF))

    assert model.has_text_layer is True
    tb = model.title_block
    assert tb.designation == "К200-150-400ENERAL.20"
    assert tb.part_name == "Вал"
    assert tb.material == "45 ГОСТ 1050-2013"
    assert tb.blank_designation == "Круг 67 ГОСТ 2590-2006"
    assert tb.scale == "1:2"
    assert tb.sheet_format == "A3"
    assert tb.mass == "13,22"


def test_val_drawing_technical_requirements_extracted_in_order():
    parser = PdfDrawingParser()
    model = parser.parse(_require(VAL_PDF))

    assert len(model.technical_requirements) == 7
    numbers = [r.number for r in model.technical_requirements]
    assert numbers == [1, 2, 3, 4, 5, 6, 7]
    assert "HRC 38" in model.technical_requirements[0].text
    assert "ГОСТ14034-74" in model.technical_requirements[1].text


def test_val_drawing_requirements_exclude_dates_and_dimensions():
    """Регрессия: даты вида '24.02.2023' и допуски вида '0.025' не должны
    ложно распознаваться как пункты технических требований."""
    parser = PdfDrawingParser()
    model = parser.parse(_require(VAL_PDF))

    texts = [r.text for r in model.technical_requirements]
    assert not any("2023" in t for t in texts)
    assert not any(t.strip() == "025" for t in texts)


def test_gear_drawing_handles_multiline_part_name_and_split_material():
    """Регрессия: наименование детали на этом чертеже перенесено на 3
    строки, а материал разбит на 'Сталь МАРКА' + 'ГОСТ N' отдельными
    строками — оба случая отличаются от layout первого fixture."""
    parser = PdfDrawingParser()
    model = parser.parse(_require(GEAR_PDF))

    tb = model.title_block
    assert tb.designation == "KPP-5002-11.10.2024"
    assert tb.part_name == "Шестерня от конической передачи с круговым зубом редуктора"
    assert tb.material == "Сталь 12ХН3А ГОСТ 4543-2016"
    assert tb.scale == "1:2"
    assert tb.sheet_format == "A2"


def test_gear_drawing_technical_requirements():
    parser = PdfDrawingParser()
    model = parser.parse(_require(GEAR_PDF))

    assert len(model.technical_requirements) == 4
    assert "ГОСТ 8479-70" in model.technical_requirements[1].text


def test_scanned_pdf_without_text_layer_reports_no_text_layer(tmp_path: Path):
    """PDF без встроенного текстового слоя (скан) должен явно сигнализировать
    has_text_layer=False, а не тихо возвращать пустые поля как будто это
    норма — иначе неотличимо от чертежа, где поля реально отсутствуют."""
    import fitz

    blank_pdf = tmp_path / "scan_no_text.pdf"
    document = fitz.open()
    document.new_page(width=595, height=842)
    document.save(blank_pdf)
    document.close()

    parser = PdfDrawingParser()
    model = parser.parse(blank_pdf)

    assert model.has_text_layer is False
    assert model.technical_requirements == ()

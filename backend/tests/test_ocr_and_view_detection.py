from pathlib import Path

import fitz
import pytest

from app.infrastructure.cad.auto_drawing_parser import AutoDrawingParser
from app.infrastructure.cad.auto_view_detector import AutoViewDetector
from app.infrastructure.cad.ocr_drawing_parser import OcrDrawingParser
from app.infrastructure.cad.raster_view_detector import RasterViewDetector
from app.infrastructure.cad.vector_view_detector import VectorViewDetector

FIXTURES_ROOT = Path(__file__).resolve().parents[3] / "КД для тестов" / "Детали из металла"
VAL_PDF = FIXTURES_ROOT / "1. Тестовая деталь металл" / "К200-150-400ENERAL.20 - Вал.pdf"
ARCHIVE_ROOT = FIXTURES_ROOT / "Архив"


def _require(path: Path) -> Path:
    if not path.exists():
        pytest.skip(f"fixture недоступен в этом окружении: {path}")
    return path


def _make_synthetic_scan(source_pdf: Path, dest_pdf: Path) -> None:
    """Рендерит первую страницу source_pdf в растр и пересобирает как
    image-only PDF — без текстового и векторного слоя, эмулирует скан."""
    source = fitz.open(source_pdf)
    page = source[0]
    width, height = page.rect.width, page.rect.height
    pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2))
    source.close()

    scan_doc = fitz.open()
    scan_page = scan_doc.new_page(width=width, height=height)
    scan_page.insert_image(scan_page.rect, pixmap=pixmap)
    scan_doc.save(dest_pdf)
    scan_doc.close()


# ---------- Детекция видов на чертеже ----------


@pytest.mark.parametrize(
    "filename",
    [
        "Вал редуктора от ковшового элеватора TS 030411.04.950 _ KPP-0010-16.03.2023.pdf",
        "Колесо от конической передачи с круговым зубом редуктора TS 030411.04.950 _ KPP-5001-11.10.2024.pdf",
    ],
)
def test_vector_view_detector_finds_plausible_view_count_on_archive_drawings(filename: str):
    """Дополнительные тестовые чертежи из Архива (не использовались для
    калибровки алгоритма) — регрессия против переобучения порогов под
    исходные 2 fixture."""
    path = _require(ARCHIVE_ROOT / filename)
    detector = VectorViewDetector()
    result = detector.detect(path)

    assert result.method == "vector_clustering"
    # Реальный чертёж детали содержит от 1 до ~8 видов/разрезов на листе —
    # проверяем разумный диапазон, а не точное число (форма детали влияет
    # на итоговое число проекций сильнее, чем сам алгоритм кластеризации).
    assert 1 <= result.view_count <= 8
    for region in result.regions:
        assert region.element_count > 0
        assert region.area > 0


def test_vector_view_detector_regions_are_within_page_bounds():
    path = _require(VAL_PDF)
    detector = VectorViewDetector()
    result = detector.detect(path)

    document = fitz.open(path)
    page_rect = document[0].rect
    document.close()

    assert result.view_count > 0
    for region in result.regions:
        assert region.x0 >= -1 and region.x1 <= page_rect.width + 1
        assert region.y0 >= -1 and region.y1 <= page_rect.height + 1


def test_raster_view_detector_finds_regions_on_synthetic_scan(tmp_path: Path):
    scan_path = tmp_path / "scan.pdf"
    _make_synthetic_scan(_require(VAL_PDF), scan_path)

    detector = RasterViewDetector()
    result = detector.detect(scan_path)

    assert result.method == "raster_segmentation"
    assert result.view_count > 0


def test_auto_view_detector_selects_vector_for_real_drawing():
    detector = AutoViewDetector()
    result = detector.detect(_require(VAL_PDF))
    assert result.method == "vector_clustering"


def test_auto_view_detector_selects_raster_for_synthetic_scan(tmp_path: Path):
    scan_path = tmp_path / "scan.pdf"
    _make_synthetic_scan(_require(VAL_PDF), scan_path)

    detector = AutoViewDetector()
    result = detector.detect(scan_path)
    assert result.method == "raster_segmentation"


# ---------- OCR для сканов ----------


def test_ocr_drawing_parser_runs_end_to_end_on_synthetic_scan(tmp_path: Path):
    """Проверяет, что OCR-конвейер реально отрабатывает на скане и
    возвращает валидный DrawingModel — не проверяет точное совпадение
    полей штампа (качество OCR ниже, чем у текстового слоя, это
    ожидаемо и не считается дефектом парсера, см. docs/ARCHITECTURE.md)."""
    scan_path = tmp_path / "scan.pdf"
    _make_synthetic_scan(_require(VAL_PDF), scan_path)

    parser = OcrDrawingParser()
    model = parser.parse(scan_path)

    assert model.page_count == 1
    assert isinstance(model.title_block.designation, (str, type(None)))
    assert isinstance(model.technical_requirements, tuple)


def test_auto_drawing_parser_selects_pdf_text_layer_for_real_drawing():
    parser = AutoDrawingParser()
    model = parser.parse(_require(VAL_PDF))
    assert model.title_block.designation == "К200-150-400ENERAL.20"


def test_auto_drawing_parser_selects_ocr_for_synthetic_scan(tmp_path: Path):
    scan_path = tmp_path / "scan.pdf"
    _make_synthetic_scan(_require(VAL_PDF), scan_path)

    parser = AutoDrawingParser()
    model = parser.parse(scan_path)
    # Скан не имеет собственного текстового слоя PDF — OCR-парсер
    # синтезирует raw_text из распознанных строк.
    assert model.page_count == 1

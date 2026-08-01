from pathlib import Path

import pytest

from app.domain.kd_review.text_generator_port import GeneratedText
from app.infrastructure.cad.pdf_drawing_parser import PdfDrawingParser
from app.infrastructure.db.sqlite_nsi_lookup import SqliteNsiLookup
from app.services.kd_review_service import KdReviewService

FIXTURES_ROOT = Path(__file__).resolve().parents[3] / "КД для тестов" / "Детали из металла"
VAL_PDF = FIXTURES_ROOT / "1. Тестовая деталь металл" / "К200-150-400ENERAL.20 - Вал.pdf"


def _require(path: Path) -> Path:
    if not path.exists():
        pytest.skip(f"fixture недоступен в этом окружении: {path}")
    return path


class _WorkingTextGenerator:
    def summarize_review(self, *, facts: dict) -> GeneratedText:
        return GeneratedText(text="Резюме от LLM.", generated_by="llm")


class _BrokenTextGenerator:
    def summarize_review(self, *, facts: dict):
        raise RuntimeError("сеть недоступна")


def test_review_uses_llm_summary_when_generator_available(tmp_path):
    drawing_path = _require(VAL_PDF)
    drawing_model = PdfDrawingParser().parse(drawing_path)
    metal_db_path = tmp_path / "metal.sqlite"
    from app.infrastructure.db.nsi_db import NsiDatabase, build_database

    build_database(NsiDatabase.METAL, metal_db_path)

    service = KdReviewService(
        nsi_lookup=SqliteNsiLookup(metal_db_path), text_generator=_WorkingTextGenerator()
    )
    report = service.review(drawing_model)

    assert report.summary.generated_by == "llm"
    assert report.summary.text == "Резюме от LLM."


def test_review_falls_back_to_template_when_generator_raises(tmp_path):
    """Ключевой принцип: сбой LLM (сеть, ключ, формат ответа) не должен
    ронять отчёт целиком — офлайн-путь остаётся рабочим всегда."""
    drawing_path = _require(VAL_PDF)
    drawing_model = PdfDrawingParser().parse(drawing_path)
    metal_db_path = tmp_path / "metal.sqlite"
    from app.infrastructure.db.nsi_db import NsiDatabase, build_database

    build_database(NsiDatabase.METAL, metal_db_path)

    service = KdReviewService(
        nsi_lookup=SqliteNsiLookup(metal_db_path), text_generator=_BrokenTextGenerator()
    )
    report = service.review(drawing_model)

    assert report.summary.generated_by == "template"
    assert report.summary.text


def test_review_uses_template_when_no_generator_configured(tmp_path):
    drawing_path = _require(VAL_PDF)
    drawing_model = PdfDrawingParser().parse(drawing_path)
    metal_db_path = tmp_path / "metal.sqlite"
    from app.infrastructure.db.nsi_db import NsiDatabase, build_database

    build_database(NsiDatabase.METAL, metal_db_path)

    service = KdReviewService(nsi_lookup=SqliteNsiLookup(metal_db_path))
    report = service.review(drawing_model)

    assert report.summary.generated_by == "template"

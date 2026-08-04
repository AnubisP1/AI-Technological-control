from pathlib import Path

import pytest

from app.domain.kd_review.material_matching import match_blank, match_material
from app.domain.kd_review.nsi_lookup_port import MaterialRecord, WorkpieceBlankRecord
from app.domain.kd_review.review_model import MatchStatus
from app.domain.kd_review.tt_categories import classify_requirement
from app.infrastructure.cad.pdf_drawing_parser import PdfDrawingParser
from app.infrastructure.db.sqlite_nsi_lookup import SqliteNsiLookup
from app.services.kd_review_service import KdReviewService

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


# ---------- Сопоставление материала/заготовки (чистая доменная логика) ----------


def test_match_material_exact_match_by_normalized_grade_and_gost():
    materials = (MaterialRecord(grade="Сталь 45", gost_standard="ГОСТ 1050-2013"),)
    result = match_material("45 ГОСТ 1050-2013", materials)
    assert result.status == MatchStatus.MATCHED
    assert result.matched_grade == "Сталь 45"


def test_match_material_partial_match_when_grade_unknown_but_gost_known():
    """Изолированный случай доменной функции: если бы в справочнике была
    только 40Х (без самой 12ХН3А — в demo-НСИ она добавлена отдельной
    записью, см. seed_data.sql), совпадение по одному ГОСТу термообработки
    должно быть частичным, не полным."""
    materials = (MaterialRecord(grade="40Х", gost_standard="ГОСТ 4543-2016"),)
    result = match_material("Сталь 12ХН3А ГОСТ 4543-2016", materials)
    assert result.status == MatchStatus.PARTIAL_MATCH


def test_match_material_finds_exact_match_even_when_partial_candidate_comes_first():
    """Регрессия: раньше match_material останавливалась на первом
    попавшемся частичном совпадении по порядку перебора и не проверяла
    остальные записи — если два материала в справочнике имели общий ГОСТ
    (как 40Х и 12ХН3А, оба ГОСТ 4543-2016), запись, идущая раньше,
    маскировала точное совпадение, идущее дальше по списку."""
    materials = (
        MaterialRecord(grade="40Х", gost_standard="ГОСТ 4543-2016"),
        MaterialRecord(grade="12ХН3А", gost_standard="ГОСТ 4543-2016"),
    )
    result = match_material("Сталь 12ХН3А ГОСТ 4543-2016", materials)
    assert result.status == MatchStatus.MATCHED
    assert result.matched_grade == "12ХН3А"


def test_match_material_not_found_when_nothing_matches():
    materials = (MaterialRecord(grade="Сталь 45", gost_standard="ГОСТ 1050-2013"),)
    result = match_material("Титан ВТ6 ГОСТ 19807-91", materials)
    assert result.status == MatchStatus.NOT_FOUND


def test_match_material_not_found_when_drawing_has_no_material():
    materials = (MaterialRecord(grade="Сталь 45", gost_standard="ГОСТ 1050-2013"),)
    result = match_material(None, materials)
    assert result.status == MatchStatus.NOT_FOUND


def test_match_blank_partial_match_when_gost_matches_but_diameter_does_not():
    """Реальный случай из fixture 1: заготовка 'Круг 67 ГОСТ 2590-2006' —
    ГОСТ проката совпадает с seed-записью, но диаметр 67мм отсутствует
    (в demo-НСИ есть только 40 и 60)."""
    blanks = (
        WorkpieceBlankRecord(
            designation="Круг Ø40 Сталь 45 ГОСТ 2590-2006",
            gost_standard="ГОСТ 2590-2006",
            diameter_mm=40,
        ),
    )
    result = match_blank("Круг 67 ГОСТ 2590-2006", blanks)
    assert result.status == MatchStatus.PARTIAL_MATCH


def test_match_blank_exact_match_when_gost_and_diameter_match():
    blanks = (
        WorkpieceBlankRecord(
            designation="Круг Ø40 Сталь 45 ГОСТ 2590-2006",
            gost_standard="ГОСТ 2590-2006",
            diameter_mm=40,
        ),
    )
    result = match_blank("Круг Ø40 ГОСТ 2590-2006", blanks)
    assert result.status == MatchStatus.MATCHED


# ---------- Классификация категорий ТТ ----------


@pytest.mark.parametrize(
    ("text", "expected_category"),
    [
        ("1. HRC 38 ... 42", "heat_treatment"),
        ("4. Неуказанные радиусы скругления R 0.4мм", "unspecified_tolerances"),
        ("5. Острые кромки притупить R0.4мм", "rounding_edges"),
        ("6. Размер для справок", "reference_dimension"),
        ("3. Общие допуски по ГОСТ 30893.1 - f", "form_position_tolerance"),
    ],
)
def test_classify_requirement_recognizes_known_categories(text: str, expected_category: str):
    assert classify_requirement(text) == expected_category


def test_classify_requirement_returns_none_for_unrecognized_text():
    """'Производитель насоса: ENERAL' — не техническое требование в
    стандартном смысле (примечание о комплектации), не должно
    ложно попадать ни в одну категорию."""
    assert classify_requirement("7. Проивзодитель насоса: ENERAL") is None


# ---------- Сервис в целом, на реальных fixture через настоящую SQLite НСИ ----------


def test_review_service_on_val_drawing_finds_material_and_partial_blank_match(tmp_path: Path):
    from app.infrastructure.db.nsi_db import NsiDatabase, build_database

    db_path = tmp_path / "metal.sqlite"
    build_database(NsiDatabase.METAL, db_path)

    drawing = PdfDrawingParser().parse(_require(VAL_PDF))
    service = KdReviewService(nsi_lookup=SqliteNsiLookup(db_path))
    report = service.review(drawing)

    assert report.material_check.status == MatchStatus.MATCHED
    assert report.blank_check.status == MatchStatus.PARTIAL_MATCH
    assert len(report.technical_requirement_checks) == 7
    # Материал найден точно -> не должно быть blocking-находки по материалу.
    assert not report.has_blocking_findings


def test_review_service_on_gear_drawing_finds_material_and_partial_blank_match(tmp_path: Path):
    """12ХН3А (ГОСТ 4543-2016) заведена в demo-НСИ явным материалом
    (см. seed_data.sql) — реальный материал реального тестового чертежа,
    не выдумка ради теста. Заготовка — поковка (обозначение группы
    контроля 'Гр. III ГОСТ 8479-70', не типовой профиль проката) —
    диаметра нет ни на чертеже, ни в справочнике, поэтому частичное
    совпадение (ГОСТ найден, типоразмер — нет), а не полное."""
    from app.infrastructure.db.nsi_db import NsiDatabase, build_database

    db_path = tmp_path / "metal.sqlite"
    build_database(NsiDatabase.METAL, db_path)

    drawing = PdfDrawingParser().parse(_require(GEAR_PDF))
    service = KdReviewService(nsi_lookup=SqliteNsiLookup(db_path))
    report = service.review(drawing)

    assert report.material_check.status == MatchStatus.MATCHED
    assert report.blank_check.status == MatchStatus.PARTIAL_MATCH


def test_review_service_without_drawing_returns_blocking_finding():
    service = KdReviewService(nsi_lookup=None)  # не должен обращаться к nsi_lookup
    report = service.review(None)

    assert report.has_blocking_findings is True
    assert report.material_check is None


def test_review_service_passes_full_material_context_to_text_generator(tmp_path: Path):
    """Регрессия (Фаза 18): _summarize должен передавать генератору не
    только findings, но и полный список материалов НСИ с их
    технологическими свойствами — иначе LLM не может реально сравнить
    материалы и предложить аналог, только переформулировать один факт."""
    from app.infrastructure.db.nsi_db import NsiDatabase, build_database

    db_path = tmp_path / "metal.sqlite"
    build_database(NsiDatabase.METAL, db_path)

    captured_facts = {}

    class _CapturingTextGenerator:
        def summarize_review(self, *, facts: dict):
            captured_facts.update(facts)
            from app.domain.kd_review.text_generator_port import GeneratedText

            return GeneratedText(text="ok", generated_by="llm")

    drawing = PdfDrawingParser().parse(_require(VAL_PDF))
    service = KdReviewService(
        nsi_lookup=SqliteNsiLookup(db_path), text_generator=_CapturingTextGenerator()
    )
    service.review(drawing)

    assert captured_facts["matched_material"]["grade"] == "Сталь 45"
    assert len(captured_facts["candidate_materials"]) >= 5
    grades = {m["grade"] for m in captured_facts["candidate_materials"]}
    assert "40Х" in grades
    assert "12ХН3А" in grades
    material_45 = next(m for m in captured_facts["candidate_materials"] if m["grade"] == "Сталь 45")
    assert material_45["machinability_index"] == 1

from app.domain.kd_review.material_matching import match_blank
from app.domain.kd_review.nsi_lookup_port import WorkpieceBlankRecord
from app.domain.kd_review.review_model import MatchStatus
from app.domain.material_text import extract_blank_diameter_mm


def test_extract_blank_diameter_mm_from_krug_designation():
    """Реальный формат чертежей проекта — 'Круг 67 ГОСТ 2590-2006', без
    символа Ø (см. stamp_extraction.py)."""
    assert extract_blank_diameter_mm("Круг 67 ГОСТ 2590-2006") == 67.0


def test_extract_blank_diameter_mm_handles_comma_decimal():
    assert extract_blank_diameter_mm("Пруток 40,5 ГОСТ 2590-2006") == 40.5


def test_extract_blank_diameter_mm_returns_none_for_non_round_profile():
    assert extract_blank_diameter_mm("Лист 5 ГОСТ 19903-2015") is None


def test_extract_blank_diameter_mm_returns_none_for_unrecognized_text():
    assert extract_blank_diameter_mm("") is None


def test_match_blank_finds_diameter_without_o_symbol_regression():
    """Регрессия: до Фазы 17 match_blank искал диаметр только по шаблону
    Ø/O + число и не находил его в реальном формате 'Круг 67 ГОСТ...' —
    диаметр молча считался отсутствующим, хотя фактически был на
    чертеже. Теперь должен использоваться fallback-парсер профиля."""
    known_blanks = (
        WorkpieceBlankRecord(
            designation="Круг 67 ГОСТ 2590-2006", gost_standard="ГОСТ 2590-2006", diameter_mm=67.0
        ),
    )
    result = match_blank("Круг 67 ГОСТ 2590-2006", known_blanks)

    assert result.status == MatchStatus.MATCHED
    assert result.matched_designation == "Круг 67 ГОСТ 2590-2006"


def test_match_blank_partial_match_distinguishes_diameter_mismatch_from_absent():
    """После исправления диаметр теперь находится в 'Круг 67...', поэтому
    несовпадение с другим справочным диаметром (40мм) должно явно
    называться несовпадением, а не 'диаметр отсутствует в НСИ' —
    иначе технолог получает вводящее в заблуждение сообщение."""
    known_blanks = (
        WorkpieceBlankRecord(
            designation="Круг 40 ГОСТ 2590-2006", gost_standard="ГОСТ 2590-2006", diameter_mm=40.0
        ),
    )
    result = match_blank("Круг 67 ГОСТ 2590-2006", known_blanks)

    assert result.status == MatchStatus.PARTIAL_MATCH
    assert "не совпадает" in result.note
    assert "67" in result.note and "40" in result.note

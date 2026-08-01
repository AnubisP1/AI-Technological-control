from pathlib import Path

import pytest

from app.infrastructure.cad.regex_step_parser import RegexStepParser

FIXTURES_ROOT = Path(__file__).resolve().parents[3] / "КД для тестов"
NPO_2026_ROOT = Path(__file__).resolve().parents[3] / "Литература" / "НПО 2026"

VAL_STEP = FIXTURES_ROOT / "Детали из металла" / "1. Тестовая деталь металл" / "3D_К200-150-400 - Вал.stp"
GEAR_STEP = (
    FIXTURES_ROOT
    / "Детали из металла"
    / "2. Тестовая деталь металл"
    / "Шестерня от конической передачи с круговым зубом редуктора TS 030411.04.950 _ KPP-5002-11.10.2024.stp"
)
KRONSHTEYN_STEP = NPO_2026_ROOT / "Кронштейн.STEP"


def _require(path: Path) -> Path:
    if not path.exists():
        pytest.skip(f"fixture недоступен в этом окружении: {path}")
    return path


def test_parses_cyrillic_c3d_step_with_escape_sequences():
    """Файлы C3D Converter кодируют кириллицу через \\X2\\HHHH\\X0\\,
    а не прямым UTF-8/windows-1251 — нужно раскодировать escape отдельно."""
    parser = RegexStepParser()
    model = parser.parse(_require(VAL_STEP))

    assert model.product_name == "Модель"
    assert model.software == "C3D Converter"
    assert model.face_count > 0


def test_val_bounding_box_matches_drawing_dimension():
    """Чертёж К200-150-400ENERAL.20 указывает общую длину вала 707±1 мм —
    bounding box по X должен совпадать (см. dev/docs/INPUTS.md)."""
    parser = RegexStepParser()
    model = parser.parse(_require(VAL_STEP))

    assert model.bounding_box is not None
    assert model.bounding_box.length_x == pytest.approx(707.488, abs=0.5)


def test_gear_step_parses_cyrillic_product_name_with_extra_spaces():
    parser = RegexStepParser()
    model = parser.parse(_require(GEAR_STEP))

    assert "Шестерня" in model.product_name
    assert model.face_count > 0
    assert model.bounding_box is not None


def test_kronshteyn_reference_model_matches_known_face_count():
    """Эталонная модель из Литература/НПО 2026/ — по CLAUDE.md этой подпапки
    ожидается 20 граней (6 плоских, 4 галтели, 9 фасок, 1 отверстие)."""
    parser = RegexStepParser()
    model = parser.parse(_require(KRONSHTEYN_STEP))

    assert model.face_count == 20
    assert model.software == "SolidWorks 2020"


def test_kronshteyn_colour_scheme_matches_known_distribution():
    """Цветовая схема из CLAUDE.md НПО 2026: синий=фаска, голубой=плоскость,
    зелёный=галтель, красный=отверстие. Допуск ±0.05 на канал (как в схеме)."""
    parser = RegexStepParser()
    model = parser.parse(_require(KRONSHTEYN_STEP))

    def _count(r: float, g: float, b: float) -> int:
        return sum(
            1
            for c in model.face_colours
            if abs(c.r - r) < 0.05 and abs(c.g - g) < 0.05 and abs(c.b - b) < 0.05
        )

    assert _count(0, 0, 1) == 9  # фаска
    assert _count(0, 1, 1) == 6  # плоскость
    assert _count(0, 1, 0) == 4  # галтель
    assert _count(1, 0, 0) == 1  # отверстие


def test_model_without_colour_annotations_returns_empty_tuple(tmp_path: Path):
    minimal_step = tmp_path / "no_colour.stp"
    minimal_step.write_text(
        "ISO-10303-21;\nHEADER;\nFILE_NAME('test','2026-01-01',(''),(''),'','','');\n"
        "ENDSEC;\nDATA;\n#1=PRODUCT('','TestPart','',(#2));\n"
        "#3=CARTESIAN_POINT('',(0.,0.,0.));\n"
        "#4=CARTESIAN_POINT('',(10.,10.,10.));\n"
        "ENDSEC;\nEND-ISO-10303-21;\n",
        encoding="utf-8",
    )
    parser = RegexStepParser()
    model = parser.parse(minimal_step)

    assert model.face_colours == ()
    assert model.has_colour_annotations is False
    assert model.bounding_box.length_x == 10.0

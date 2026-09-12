"""Распознавание КД серии МВАУ: совмещённая запись графы 3, нумерация ТТ
без точки, честность на нечитаемых сканах.

Корпус чертежей лежит ВНЕ репозитория, поэтому тесты на реальных файлах
пропускаются, если его нет (тот же приём _require, что и в
test_kd_review_endpoint.py). Разбор строк графы 3 проверяется без
файлов — на тех же строках, что реально встречаются в корпусе.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.domain.cad.drawing_model import DrawingModel, TitleBlockFields
from app.domain.kd_review.review_model import KdReviewFinding
from app.domain.kd_review.tt_categories import classify_requirement
from app.domain.material_text import (
    extract_material_from_blank_designation,
    extract_plate_thickness_mm,
)
from app.infrastructure.cad.auto_drawing_parser import AutoDrawingParser
from app.infrastructure.cad.pdf_drawing_parser import PdfDrawingParser

MVAU_ROOT = Path("/Users/bdd/Documents/Работа/Подписанная КД (1)")
BRACKET_SCAN = MVAU_ROOT / "МВАУ.104759.001-01.111.020.pdf"
SHEET_DETAIL = MVAU_ROOT / "МВАУ.104759.001-01.172.009_Закладная.pdf"
ASSEMBLY = MVAU_ROOT / "МВАУ.104759.001-01.100.000 СБ_Планер.pdf"
SPECIFICATION = MVAU_ROOT / "МВАУ.104759.001-01.131.000 СП.pdf"


def _require(path: Path) -> Path:
    if not path.exists():
        pytest.skip(f"fixture недоступен в этом окружении: {path}")
    return path


class TestMaterialFromCombinedRow:
    """Графа 3 серии МВАУ несёт профиль и марку одной строкой."""

    @pytest.mark.parametrize(
        ("blank_row", "expected"),
        [
            ("Лист Д16Т 2 ГОСТ 21631-2023", "Д16Т ГОСТ 21631-2023"),
            ("Лист 2 Д16 ГОСТ 21631-2019", "Д16 ГОСТ 21631-2019"),
            ("Лист АД31 ГОСТ 4784-97", "АД31 ГОСТ 4784-97"),
            ("Плита Д16 АТ 35x80x80 ГОСТ 17232-2023", "Д16 ГОСТ 17232-2023"),
            ("Плита Д16 А Т 20x1200x3000 ГОСТ 17232-2023", "Д16 ГОСТ 17232-2023"),
        ],
    )
    def test_марка_извлекается(self, blank_row: str, expected: str):
        assert extract_material_from_blank_designation(blank_row) == expected

    @pytest.mark.parametrize(
        "blank_row",
        [
            # Регрессия: круглый прокат марки не содержит — марка приходит
            # отдельной строкой штампа и разбирается другим путём.
            "Круг 67 ГОСТ 2590-2006",
            "Уголок 10х15х1,5 ГОСТ 22233-2018",
            # Без ссылки на стандарт запись не является обозначением
            # материала по ГОСТ Р 2.109 п. 6.3.
            "Лист Д16",
        ],
    )
    def test_марка_не_выдумывается(self, blank_row: str):
        assert extract_material_from_blank_designation(blank_row) is None


class TestPlateThickness:
    def test_тройка_размеров(self):
        assert extract_plate_thickness_mm("Плита Д16 АТ 35х80х80 ГОСТ 17232-2023") == 35.0

    def test_одиночное_число(self):
        """У листа в чертеже детали указывают только толщину."""
        assert extract_plate_thickness_mm("Лист Д16Т 2 ГОСТ 21631-2023") == 2.0

    def test_круглый_прокат_не_плоский(self):
        assert extract_plate_thickness_mm("Круг 67 ГОСТ 2590-2006") is None


class TestTechnicalRequirementsPositional:
    def test_спецификация_не_даёт_ложных_пунктов(self):
        """Строки спецификации нумеруются так же, как пункты ТТ
        («1 МВАУ.104759.001-01.140.001 Обшивка»). Без позиционного
        фильтра каждая спецификация превратилась бы в десятки
        фиктивных технических требований."""
        model = PdfDrawingParser().parse(_require(SPECIFICATION))
        assert model.technical_requirements == ()

    def test_нумерация_без_точки_распознаётся(self):
        model = PdfDrawingParser().parse(_require(ASSEMBLY))
        assert len(model.technical_requirements) == 6
        assert model.technical_requirements[0].text.startswith("Все размеры для справок")

    def test_перенос_строки_склеивается(self):
        """Пункт 2 перенесён на вторую строку; без склейки классификатор
        получил бы обрубок фразы."""
        model = PdfDrawingParser().parse(_require(ASSEMBLY))
        assert model.technical_requirements[1].text.endswith("из состава крыла")

    def test_материал_и_заготовка_из_одной_строки(self):
        model = PdfDrawingParser().parse(_require(SHEET_DETAIL))
        assert model.title_block.material == "Д16Т ГОСТ 21631-2023"
        assert model.title_block.blank_designation == "Лист Д16Т 2 ГОСТ 21631-2023"


class TestMarkingCategory:
    @pytest.mark.parametrize(
        "text",
        [
            "Клеймить К, маркировать Ч на бирке",
            "Клеймить К, маркировать Ч и порядковый номер сб. ед. по технологии",
        ],
    )
    def test_клеймение_классифицируется(self, text: str):
        assert classify_requirement(text) == "marking"

    def test_сборка_по_стыковым_отверстиям(self):
        assert classify_requirement("Сборку производить по стыковым отв.") == "assembly"


class TestLowResolutionScan:
    def test_скан_низкого_разрешения_определяется(self):
        parsed = AutoDrawingParser().parse(_require(BRACKET_SCAN))
        assert parsed.source_kind == "ocr"
        assert parsed.raster_dpi is not None and parsed.raster_dpi < 60
        assert parsed.is_low_resolution_scan is True

    def test_чертёж_с_текстовым_слоем_не_помечается_сканом(self):
        parsed = PdfDrawingParser().parse(_require(SHEET_DETAIL))
        assert parsed.source_kind == "text_layer"
        assert parsed.is_low_resolution_scan is False

    def test_нечитаемый_скан_не_блокирует_согласование(self):
        """Материал на чертеже указан и корректен — не прочитан он из-за
        качества файла. Блокировать согласование в этом случае значит
        сделать ложный вывод о конструкции, а не о материале."""
        from app.services.kd_review_service import KdReviewService

        class _EmptyNsi:
            def find_materials(self):
                return ()

            def find_workpiece_blanks(self):
                return ()

        scan = DrawingModel(
            file_path="scan.pdf",
            page_count=1,
            title_block=TitleBlockFields(),
            raw_text="нечитаемый скан",
            source_kind="ocr",
            raster_dpi=46.0,
        )
        report = KdReviewService(nsi_lookup=_EmptyNsi()).review(scan)

        assert report.has_blocking_findings is False
        first: KdReviewFinding = report.findings[0]
        assert first.severity == "warning"
        assert "разрешением" in first.message

"""Распознавание КД серии МВАУ: совмещённая запись графы 3, нумерация ТТ
без точки, честность на нечитаемых сканах.

Корпус чертежей лежит ВНЕ репозитория, поэтому тесты на реальных файлах
пропускаются, если его нет (тот же приём _require, что и в
test_kd_review_endpoint.py). Разбор строк графы 3 проверяется без
файлов — на тех же строках, что реально встречаются в корпусе.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from app.domain.cad.drawing_model import DrawingModel, TitleBlockFields
from app.domain.kd_review.review_model import GostCheckStatus, KdReviewFinding
from app.domain.kd_review.tt_categories import classify_requirement
from app.domain.material_text import (
    extract_material_from_blank_designation,
    extract_plate_thickness_mm,
)
from app.infrastructure.cad.auto_drawing_parser import AutoDrawingParser
from app.infrastructure.cad.pdf_drawing_parser import PdfDrawingParser

MVAU_ROOT = Path("/Users/bdd/Documents/Работа/Подписанная КД (1)")
# Этот чертёж пользователь положил в общий каталог фикстур проекта.
BRACKET_SCAN = (
    Path(__file__).resolve().parents[3] / "КД для тестов" / "МВАУ.104759.001-01.111.020.pdf"
)
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
    def test_векторный_чертёж_без_текста_не_считается_плохим_сканом(self):
        """Регрессия: этот чертёж — ВЕКТОРНЫЙ, текстового слоя нет, но
        качество идеальное. Внутри есть маленькая картинка подписи (6%
        листа); считать по ней разрешение всего листа неверно — раньше
        из-за этого чертёж объявлялся нечитаемым сканом 46 DPI."""
        parsed = AutoDrawingParser().parse(_require(BRACKET_SCAN))
        assert parsed.source_kind == "ocr"  # текстового слоя действительно нет
        assert parsed.raster_dpi is None  # но лист не растровый
        assert parsed.is_low_resolution_scan is False

    def test_материал_читается_прицельным_разбором_штампа(self):
        """Общий проход по листу теряет мелкий шрифт основной надписи;
        отдельный проход по штампу с увеличением и удалением линий
        разграфки её читает."""
        parsed = AutoDrawingParser().parse(_require(BRACKET_SCAN))
        assert parsed.title_block.material == "Д16 ГОСТ 17232-2023"

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


class TestTypicalRequirementMatching:
    """Сверка формулировок ТТ с типовыми по ОСТ 1 02504-84."""

    def _templates(self, tmp_path: Path):
        from app.infrastructure.db.nsi_db import NsiDatabase, build_database
        from app.infrastructure.db.sqlite_tt_template_lookup import (
            SqliteTypicalRequirementLookup,
        )

        db = tmp_path / "metal.sqlite"
        build_database(NsiDatabase.METAL, db)
        return SqliteTypicalRequirementLookup(db).find_typical_requirements()

    def test_формулировка_с_уточнением_совпадает_с_типовой(self, tmp_path: Path):
        """Конструктор дописал «допуски формы и расположения поверхностей»
        к типовой формулировке — это по-прежнему она."""
        from app.domain.cad.drawing_model import TechnicalRequirement
        from app.domain.kd_review.tt_template_matching import match_typical_requirement

        requirement = TechnicalRequirement(
            number=1,
            text=(
                "Неуказанные предельные отклонения размеров, допуски формы и "
                "расположения поверхностей по ОСТ 1 00022-80"
            ),
        )
        match = match_typical_requirement(requirement, self._templates(tmp_path))
        assert match is not None
        assert match.code == "UNSPEC_TOLERANCE"
        assert match.reference_standard == "ОСТ 1 00022-80"

    def test_клеймение_совпадает_с_типовой(self, tmp_path: Path):
        from app.domain.cad.drawing_model import TechnicalRequirement
        from app.domain.kd_review.tt_template_matching import match_typical_requirement

        match = match_typical_requirement(
            TechnicalRequirement(number=6, text="Клеймить К, маркировать Ч на бирке"),
            self._templates(tmp_path),
        )
        assert match is not None and match.code == "MARKING_STAMPING"

    def test_посторонний_пункт_не_подгоняется_под_типовую(self, tmp_path: Path):
        """Отсутствие совпадения — нормальный результат, а не ошибка:
        стандарт не запрещает формулировать своими словами."""
        from app.domain.cad.drawing_model import TechnicalRequirement
        from app.domain.kd_review.tt_template_matching import match_typical_requirement

        match = match_typical_requirement(
            TechnicalRequirement(number=2, text="Фюзеляж поз. 2 крепить к крылу поз. 1"),
            self._templates(tmp_path),
        )
        assert match is None


class TestRequirementsOrder:
    """Последовательность изложения ТТ (ГОСТ Р 2.316-2023, п. 6.5)."""

    def _check(self, categories: list[str]):
        from app.domain.kd_review.gost_checking import (
            check_technical_requirements_order,
        )
        from app.domain.kd_review.review_model import TechnicalRequirementCheck

        checks = tuple(
            TechnicalRequirementCheck(
                number=i + 1, text=f"пункт {i + 1}", is_recognized=True, category=c
            )
            for i, c in enumerate(categories)
        )
        return check_technical_requirements_order(checks)

    def test_правильный_порядок_проходит(self):
        result = self._check(["material", "heat_treatment", "coating", "marking"])
        assert result is not None
        assert result.status is GostCheckStatus.PASSED

    def test_нарушенный_порядок_на_решение_технолога(self):
        """п. 6.5 требует последовательности «по возможности» — это
        рекомендация, поэтому NEEDS_REVIEW, а не VIOLATED."""
        result = self._check(["marking", "material"])
        assert result is not None
        assert result.status is GostCheckStatus.NEEDS_REVIEW

    def test_меньше_двух_известных_категорий_не_проверяется(self):
        assert self._check(["material"]) is None


class TestStampFieldRecovery:
    """Прицельное чтение граф основной надписи на чертеже без текстового слоя."""

    def test_обозначение_собирается_поразрядно(self):
        """Цифровые группы читаются устойчиво; спорные разряды помечаются
        «?», а не заполняются произвольной цифрой."""
        parsed = AutoDrawingParser().parse(_require(BRACKET_SCAN))
        designation = parsed.title_block.designation
        assert designation is not None
        assert designation.startswith("104759.001-")
        assert designation.endswith(".111.020")

    def test_масса_нормализуется_по_госту(self):
        """На чертеже «82гр.» — граммы с точкой. ГОСТ Р 2.104 предписывает
        указывать массу в килограммах без единицы измерения."""
        parsed = AutoDrawingParser().parse(_require(BRACKET_SCAN))
        assert parsed.title_block.mass == "0,082"

    def test_кириллическая_аббревиатура_не_подменяется_латиницей(self):
        """Общий OCR читает «ОЧК» как «UYK»: латинские буквы визуально
        неотличимы. Проход со списком только кириллических символов
        возвращает верное написание."""
        parsed = AutoDrawingParser().parse(_require(BRACKET_SCAN))
        part_name = parsed.title_block.part_name
        assert part_name == "Кронштейн навески ОЧК задний"
        assert not re.search(r"[A-Za-z]", part_name)

    def test_обозначение_второго_чертежа_серии(self):
        """Проверка на другом чертеже той же серии — распознавание не
        подогнано под один файл."""
        other = MVAU_ROOT / "МВАУ.104759.001-01.351.001 - Фальшпол.pdf"
        parsed = AutoDrawingParser().parse(_require(other))
        assert parsed.title_block.designation == "104759.001-01.351.001"

"""Тесты проверок оформления чертежа по ГОСТ ЕСКД (Фаза 23).

Проверяется доменная логика в отрыве от базы: требования подаются как
фикстуры, повторяющие реальную разметку из `БД НСИ/ГОСТ/` (ряды
масштабов ГОСТ 2.302, графы основной надписи ГОСТ Р 2.104).
"""

from __future__ import annotations

from app.domain.cad.drawing_model import (
    DrawingModel,
    GeneralRoughness,
    TechnicalRequirement,
    TitleBlockFields,
)
from app.domain.kd_review.gost_checking import (
    check_general_roughness_format,
    check_material_designation,
    check_plate_blank_sortament,
    check_scale,
    check_technical_requirements_numbering,
    check_title_block,
)
from app.domain.kd_review.gost_lookup_port import (
    GostEnumRequirement,
    GostNumericRequirement,
    GostProceduralRequirement,
    GostTitleBlockField,
)
from app.domain.kd_review.review_model import GostCheckStatus

# Ряды из ГОСТ 2.302 п.2 — ровно так они размечены в seed_gost_2302_clauses.sql.
SCALE_REQUIREMENTS = (
    GostEnumRequirement(
        standard_designation="ГОСТ 2.302-1968",
        clause_number="2-умен",
        parameter_name="масштаб уменьшения (допустимый ряд)",
        allowed_values=("1:2", "1:2,5", "1:4", "1:5", "1:10", "1:15", "1:20"),
        clause_text="Масштабы уменьшения…",
    ),
    GostEnumRequirement(
        standard_designation="ГОСТ 2.302-1968",
        clause_number="2-увел",
        parameter_name="масштаб увеличения (допустимый ряд)",
        allowed_values=("2:1", "2,5:1", "4:1", "5:1", "10:1"),
        clause_text="Масштабы увеличения…",
    ),
)

TITLE_BLOCK_FIELDS = (
    GostTitleBlockField(
        standard_designation="ГОСТ Р 2.104-2023",
        field_number="1",
        field_heading=None,
        content_kind="Реквизит КД «Наименование»",
        fill_rule="Наименование изделия",
        required_paper="●",
        required_electronic="●",
    ),
    GostTitleBlockField(
        standard_designation="ГОСТ Р 2.104-2023",
        field_number="5",
        field_heading="Масса",
        content_kind="Масса изделия",
        fill_rule="Масса изделия",
        required_paper="○",
        required_electronic="○",
    ),
)


def _drawing(**title_block_kwargs) -> DrawingModel:
    return DrawingModel(
        file_path="test.pdf",
        page_count=1,
        title_block=TitleBlockFields(**title_block_kwargs),
    )


class TestCheckScale:
    def test_масштаб_из_ряда_проходит(self):
        result = check_scale(_drawing(scale="1:2"), SCALE_REQUIREMENTS)
        assert result is not None
        assert result.status is GostCheckStatus.PASSED

    def test_десятичная_запятая_сохраняется(self):
        """«1:2,5» есть в ряду ГОСТ именно с запятой — подмена на точку
        дала бы ложное «нет в допустимом ряду»."""
        result = check_scale(_drawing(scale="1:2,5"), SCALE_REQUIREMENTS)
        assert result is not None
        assert result.status is GostCheckStatus.PASSED

    def test_префикс_М_и_пробелы_не_мешают(self):
        result = check_scale(_drawing(scale="М 1 : 5"), SCALE_REQUIREMENTS)
        assert result is not None
        assert result.status is GostCheckStatus.PASSED

    def test_масштаб_вне_ряда_нарушение(self):
        result = check_scale(_drawing(scale="1:3"), SCALE_REQUIREMENTS)
        assert result is not None
        assert result.status is GostCheckStatus.VIOLATED
        assert result.actual_value == "1:3"

    def test_нераспознанный_масштаб_на_решение_технолога(self):
        result = check_scale(_drawing(scale=None), SCALE_REQUIREMENTS)
        assert result is not None
        assert result.status is GostCheckStatus.NEEDS_REVIEW

    def test_без_требований_в_базе_проверка_не_выполняется(self):
        """None, а не PASSED: отсутствие настроенной проверки нельзя
        выдавать за её успешное прохождение."""
        assert check_scale(_drawing(scale="1:2"), ()) is None


class TestCheckTitleBlock:
    def test_заполненная_графа_проходит(self):
        checks = check_title_block(_drawing(part_name="Вал"), TITLE_BLOCK_FIELDS)
        by_field = {c.clause_number: c for c in checks}
        assert by_field["графа 1"].status is GostCheckStatus.PASSED

    def test_пустая_обязательная_графа_нарушение(self):
        checks = check_title_block(_drawing(part_name=None), TITLE_BLOCK_FIELDS)
        by_field = {c.clause_number: c for c in checks}
        assert by_field["графа 1"].status is GostCheckStatus.VIOLATED

    def test_пустая_условная_графа_на_решение_технолога(self):
        """Графа 5 «Масса» имеет обязательность «○» — её отсутствие не
        нарушение, а вопрос к виду КД."""
        checks = check_title_block(_drawing(mass=None), TITLE_BLOCK_FIELDS)
        by_field = {c.clause_number: c for c in checks}
        assert by_field["графа 5"].status is GostCheckStatus.NEEDS_REVIEW

    def test_прочерк_не_считается_заполнением(self):
        """«-» в графе «Масса» означает, что масса не указана, а не что
        графа заполнена значением «-»."""
        checks = check_title_block(_drawing(mass="-"), TITLE_BLOCK_FIELDS)
        by_field = {c.clause_number: c for c in checks}
        assert by_field["графа 5"].status is GostCheckStatus.NEEDS_REVIEW

    def test_без_размеченных_граф_ничего_не_проверяется(self):
        assert check_title_block(_drawing(part_name="Вал"), ()) == ()


class TestCheckTechnicalRequirementsNumbering:
    def _with_tt(self, numbers: list[int]) -> DrawingModel:
        return DrawingModel(
            file_path="test.pdf",
            page_count=1,
            title_block=TitleBlockFields(),
            technical_requirements=tuple(
                TechnicalRequirement(number=n, text=f"пункт {n}") for n in numbers
            ),
        )

    def test_сквозная_нумерация_проходит(self):
        result = check_technical_requirements_numbering(self._with_tt([1, 2, 3]))
        assert result is not None
        assert result.status is GostCheckStatus.PASSED

    def test_пропуск_номера_нарушение(self):
        result = check_technical_requirements_numbering(self._with_tt([1, 2, 4]))
        assert result is not None
        assert result.status is GostCheckStatus.VIOLATED

    def test_без_тт_проверка_не_выполняется(self):
        """По ГОСТ Р 2.316 п.6.1 ТТ приводят «при необходимости» —
        их отсутствие само по себе не нарушение."""
        assert check_technical_requirements_numbering(self._with_tt([])) is None


class TestCheckMaterialDesignation:
    def test_ссылка_на_гост_проходит(self):
        result = check_material_designation(_drawing(material="45 ГОСТ 1050-2013"))
        assert result.status is GostCheckStatus.PASSED

    def test_ссылка_на_ту_проходит(self):
        result = check_material_designation(_drawing(material="АМг6 ТУ 1-804-433-2007"))
        assert result.status is GostCheckStatus.PASSED

    def test_без_ссылки_на_стандарт_на_проверку(self):
        """NEEDS_REVIEW, не VIOLATED: возможна неполнота распознавания
        чертежа, а не ошибка конструктора."""
        result = check_material_designation(_drawing(material="Сталь 45"))
        assert result.status is GostCheckStatus.NEEDS_REVIEW

    def test_прочерк_равносилен_пустой_графе(self):
        result = check_material_designation(_drawing(material="—"))
        assert result.status is GostCheckStatus.NEEDS_REVIEW
        assert result.actual_value is None


ROUGHNESS_REQUIREMENTS = (
    GostProceduralRequirement(
        standard_designation="ГОСТ 2.309-73",
        clause_number="1.2",
        parameter_name=(
            "полка знака шероховатости при указании только значения параметра"
        ),
        clause_text=(
            "При применении знака без указания способа обработки его изображают "
            "без полки."
        ),
    ),
)


class TestCheckGeneralRoughness:
    def _with_roughness(self, has_extended_shelf: bool) -> DrawingModel:
        return DrawingModel(
            file_path="test.pdf",
            page_count=1,
            title_block=TitleBlockFields(),
            general_roughness=GeneralRoughness(
                parameter="Ra",
                value_um=3.2,
                raw_text="Ra 3,2",
                has_extended_shelf=has_extended_shelf,
            ),
        )

    def test_длинная_полка_при_одном_параметре_нарушение(self):
        result = check_general_roughness_format(
            self._with_roughness(True), ROUGHNESS_REQUIREMENTS
        )
        assert result is not None
        assert result.status is GostCheckStatus.VIOLATED
        assert result.standard_designation == "ГОСТ 2.309-73"
        assert result.clause_number == "1.2"

    def test_знак_без_полки_проходит(self):
        result = check_general_roughness_format(
            self._with_roughness(False), ROUGHNESS_REQUIREMENTS
        )
        assert result is not None
        assert result.status is GostCheckStatus.PASSED

    def test_без_пункта_в_бд_нет_вердикта(self):
        assert check_general_roughness_format(self._with_roughness(True), ()) is None


# Сортамент плит по ГОСТ 17232-2023, таблица 1 — ровно так размечено в
# seed_gost_17232_clauses.sql (диапазон для группы марок с Д16).
PLATE_REQUIREMENTS = (
    GostNumericRequirement(
        standard_designation="ГОСТ 17232-2023",
        clause_number="4.2.1-толщина-Д16",
        parameter_name="толщина плиты из сплава Д16 (таблица 1)",
        unit="мм",
        comparison_op="BETWEEN",
        limit_value_min=10.5,
        limit_value_max=200.0,
        clause_text="Плиты в зависимости от марки сплава…",
    ),
)


class TestCheckPlateBlankSortament:
    def _drawing_with_blank(self, blank: str) -> DrawingModel:
        return DrawingModel(
            file_path="test.pdf",
            page_count=1,
            title_block=TitleBlockFields(blank_designation=blank),
        )

    def test_толщина_в_сортаменте_проходит(self):
        result = check_plate_blank_sortament(
            self._drawing_with_blank("Плита Д16 А Т 35х80х80 ГОСТ 17232-2023"),
            PLATE_REQUIREMENTS,
        )
        assert result is not None
        assert result.status is GostCheckStatus.PASSED
        assert result.actual_value == "35 мм"

    def test_ширина_и_длина_не_сверяются(self):
        """80x80 — размер вырезанной под деталь карточки, а не
        поставляемой плиты (по таблице 1 ширина от 1000, длина от 2000).
        Сверка этих размеров дала бы заведомо ложное нарушение."""
        result = check_plate_blank_sortament(
            self._drawing_with_blank("Плита Д16 А Т 35х80х80 ГОСТ 17232-2023"),
            PLATE_REQUIREMENTS,
        )
        assert result is not None
        assert result.status is GostCheckStatus.PASSED
        assert "не сверялись" in result.note

    def test_толщина_ниже_сортамента_нарушение(self):
        result = check_plate_blank_sortament(
            self._drawing_with_blank("Плита Д16 А Т 8х500х1000 ГОСТ 17232-2023"),
            PLATE_REQUIREMENTS,
        )
        assert result is not None
        assert result.status is GostCheckStatus.VIOLATED

    def test_толщина_выше_сортамента_нарушение(self):
        result = check_plate_blank_sortament(
            self._drawing_with_blank("Плита Д16 А Т 250х1000х2000 ГОСТ 17232-2023"),
            PLATE_REQUIREMENTS,
        )
        assert result is not None
        assert result.status is GostCheckStatus.VIOLATED

    def test_суффикс_повышенной_точности_не_ломает_разбор(self):
        """«20Пх1200x3000» — повышенная точность по толщине (п. 3.1),
        пример условного обозначения из п. 4.2.8 стандарта."""
        result = check_plate_blank_sortament(
            self._drawing_with_blank("Плита Д16 А Т 20Пх1200x3000 ГОСТ 17232-2023"),
            PLATE_REQUIREMENTS,
        )
        assert result is not None
        assert result.status is GostCheckStatus.PASSED
        assert result.actual_value == "20 мм"

    def test_круглый_прокат_не_проверяется(self):
        assert (
            check_plate_blank_sortament(
                self._drawing_with_blank("Круг 67 ГОСТ 2590-2006"), PLATE_REQUIREMENTS
            )
            is None
        )

    def test_без_требований_в_базе_проверка_не_выполняется(self):
        assert (
            check_plate_blank_sortament(
                self._drawing_with_blank("Плита Д16 А Т 35х80х80 ГОСТ 17232-2023"), ()
            )
            is None
        )

"""Проверка оформления чертежа по требованиям ГОСТ ЕСКД (Модуль 1.2).

Источник требований — БД `БД НСИ/ГОСТ/` (см. её README): пункты стандартов
размечены как проверяемые утверждения, а не как текст. Здесь только
доменная логика сопоставления «что извлечено с чертежа» с «что требует
пункт»; доступ к данным — через IGostLookup.

Принцип: проверяется ТОЛЬКО то, по чему возможен однозначный вердикт.
Пункты вида «может быть ограничен линией обрыва или не ограничен»
(PROCEDURAL в БД) сюда не попадают вовсе — вынести по ним «соответствует/
нарушено» нельзя, а имитация проверки хуже её отсутствия.
"""

from __future__ import annotations

import re

from app.domain.cad.drawing_model import DrawingModel
from app.domain.kd_review.gost_lookup_port import (
    GostEnumRequirement,
    GostNumericRequirement,
    GostProceduralRequirement,
    GostTitleBlockField,
)
from app.domain.material_text import extract_plate_dimensions_mm, is_plate_blank
from app.domain.kd_review.review_model import GostCheckStatus, GostRequirementCheck

# Соответствие «поле основной надписи в DrawingModel -> номер графы по
# ГОСТ Р 2.104 (таблица 1)». Проверяются только те графы, которые парсер
# чертежа реально умеет извлекать: заявлять «графа 19 не заполнена», не
# умея её читать, — ложная находка.
_TITLE_BLOCK_FIELD_MAP: dict[str, str] = {
    "part_name": "1",  # наименование изделия
    "designation": "2",  # обозначение КД
    "material": "3",  # материал
    "mass": "5",  # масса
    "scale": "6",  # масштаб
    "sheet_format": "32",  # формат листа
}

# Обязательность по ГОСТ Р 2.104: '●' — заполнение обязательно,
# '○' — зависит от вида КД, '*' — не обязательна.
_REQUIRED = "●"
_CONDITIONAL = "○"

_ROUGHNESS_SHELF_MARKER = "полка знака шероховатости"


def check_general_roughness_format(
    drawing: DrawingModel,
    requirements: tuple[GostProceduralRequirement, ...],
) -> GostRequirementCheck | None:
    """Полка общего знака при наличии только параметра шероховатости."""
    roughness = drawing.general_roughness
    if roughness is None:
        return None
    requirement = next(
        (
            item
            for item in requirements
            if _ROUGHNESS_SHELF_MARKER in item.parameter_name.lower()
        ),
        None,
    )
    # Нет пункта в БД — нет и автоматического вердикта.
    if requirement is None:
        return None
    actual = f"{roughness.parameter} {roughness.value_um:g}; " + (
        "знак с длинной полкой" if roughness.has_extended_shelf else "знак без полки"
    )
    if roughness.has_extended_shelf:
        return GostRequirementCheck(
            standard_designation=requirement.standard_designation,
            clause_number=requirement.clause_number,
            parameter_name=requirement.parameter_name,
            status=GostCheckStatus.VIOLATED,
            actual_value=actual,
            expected=requirement.clause_text,
            note=(
                "В правом верхнем углу распознано только значение параметра, "
                "но знак имеет продолженную полку. Уберите полку либо укажите "
                "на ней предусмотренные стандартом дополнительные сведения."
            ),
        )
    return GostRequirementCheck(
        standard_designation=requirement.standard_designation,
        clause_number=requirement.clause_number,
        parameter_name=requirement.parameter_name,
        status=GostCheckStatus.PASSED,
        actual_value=actual,
        expected=requirement.clause_text,
        note="При одном значении параметра применён знак без полки.",
    )


def _normalize_scale(value: str) -> str:
    """Приводит масштаб к виду «1:2» — на чертеже встречается «1 : 2»,
    «1:2,5», «М1:2». Десятичная запятая сохраняется: в ГОСТ 2.302 ряд
    задан именно через запятую («1:2,5»), и замена её на точку привела бы
    к ложному «нет в допустимом ряду»."""
    cleaned = value.strip().upper()
    cleaned = re.sub(r"^[МM]\s*", "", cleaned)  # «М1:2» -> «1:2»
    cleaned = re.sub(r"\s+", "", cleaned)
    return cleaned


# Значения, которыми парсер помечает НЕраспознанную/пустую графу, и
# которые конструктор ставит как явный прочерк. Считать их заполнением
# нельзя: «-» в графе «Масса» означает, что масса не указана.
_EMPTY_FIELD_MARKERS = frozenset({"-", "–", "—", "нет", "н/д", "не указан", "не указано"})


def _is_field_filled(value: object) -> bool:
    if value is None:
        return False
    text = str(value).strip()
    if not text:
        return False
    return text.lower() not in _EMPTY_FIELD_MARKERS


def check_scale(
    drawing: DrawingModel, enum_requirements: tuple[GostEnumRequirement, ...]
) -> GostRequirementCheck | None:
    """Масштаб из основной надписи против закрытых рядов ГОСТ 2.302.

    Возвращает None, если в БД нет требований по масштабу — это значит,
    что проверка не настроена, и молча «проходить» её нельзя.
    """
    scale_requirements = tuple(
        r for r in enum_requirements if "масштаб" in r.parameter_name.lower()
    )
    if not scale_requirements:
        return None

    standard = scale_requirements[0].standard_designation
    raw = drawing.title_block.scale

    if not raw:
        # Масштаб не распознан. Это не то же самое, что «масштаб неверный»:
        # графа 6 по ГОСТ 2.104 имеет обязательность «○» (обязательна на
        # чертежах, но не на всех видах КД), поэтому — на решение технолога.
        return GostRequirementCheck(
            standard_designation=standard,
            clause_number="2",
            parameter_name="масштаб изображения",
            status=GostCheckStatus.NEEDS_REVIEW,
            actual_value=None,
            expected="значение из ряда ГОСТ 2.302 (п. 2)",
            note=(
                "Масштаб не распознан в основной надписи. По ГОСТ 2.104 графу "
                "«Масштаб» обязательно заполняют на чертежах — проверьте "
                "вручную, заполнена ли она."
            ),
        )

    normalized = _normalize_scale(raw)
    for requirement in scale_requirements:
        allowed_normalized = {_normalize_scale(v) for v in requirement.allowed_values}
        if normalized in allowed_normalized:
            return GostRequirementCheck(
                standard_designation=requirement.standard_designation,
                clause_number=requirement.clause_number,
                parameter_name=requirement.parameter_name,
                status=GostCheckStatus.PASSED,
                actual_value=raw,
                expected=requirement.parameter_name,
                note="Масштаб входит в допустимый ряд стандарта.",
            )

    all_allowed = sorted(
        {v for r in scale_requirements for v in r.allowed_values}
    )
    return GostRequirementCheck(
        standard_designation=standard,
        clause_number="2",
        parameter_name="масштаб изображения",
        status=GostCheckStatus.VIOLATED,
        actual_value=raw,
        expected="; ".join(all_allowed),
        note=(
            f"Масштаб «{raw}» не входит ни в один допустимый ряд ГОСТ 2.302. "
            "Ряды заданы стандартом как закрытые (п. 2-4)."
        ),
    )


def check_title_block(
    drawing: DrawingModel, title_block_fields: tuple[GostTitleBlockField, ...]
) -> tuple[GostRequirementCheck, ...]:
    """Заполненность граф основной надписи по ГОСТ Р 2.104 (таблица 1).

    Проверяются только графы из _TITLE_BLOCK_FIELD_MAP — те, что парсер
    умеет извлекать. Для граф с обязательностью «○» пустое значение даёт
    NEEDS_REVIEW, а не VIOLATED: стандарт ставит их заполнение в
    зависимость от вида КД, и решение за технологом.
    """
    if not title_block_fields:
        return ()

    by_number = {f.field_number: f for f in title_block_fields}
    checks: list[GostRequirementCheck] = []

    for attr_name, field_number in _TITLE_BLOCK_FIELD_MAP.items():
        spec = by_number.get(field_number)
        if spec is None:
            continue  # графа не размечена в БД — не выдумываем требование

        value = getattr(drawing.title_block, attr_name, None)
        heading = spec.field_heading or spec.content_kind or f"графа {field_number}"
        label = f"графа {field_number} «{heading}»"

        if _is_field_filled(value):
            checks.append(
                GostRequirementCheck(
                    standard_designation=spec.standard_designation,
                    clause_number=f"графа {field_number}",
                    parameter_name=label,
                    status=GostCheckStatus.PASSED,
                    actual_value=str(value),
                    expected=spec.content_kind,
                    note="Графа заполнена.",
                )
            )
            continue

        if spec.required_paper == _REQUIRED:
            status = GostCheckStatus.VIOLATED
            note = (
                "Графа обязательна к заполнению по ГОСТ Р 2.104 (таблица 1) — "
                "значение не распознано на чертеже."
            )
        elif spec.required_paper == _CONDITIONAL:
            status = GostCheckStatus.NEEDS_REVIEW
            note = (
                "Обязательность графы по ГОСТ Р 2.104 зависит от вида КД "
                "(обозначена «○») — требуется решение технолога."
            )
        else:
            status = GostCheckStatus.NOT_APPLICABLE
            note = "Графа не обязательна к заполнению."

        checks.append(
            GostRequirementCheck(
                standard_designation=spec.standard_designation,
                clause_number=f"графа {field_number}",
                parameter_name=label,
                status=status,
                actual_value=None,
                expected=spec.content_kind,
                note=note,
            )
        )

    return tuple(checks)


def check_technical_requirements_numbering(
    drawing: DrawingModel,
) -> GostRequirementCheck | None:
    """Сквозная нумерация пунктов ТТ по ГОСТ Р 2.316, п. 6.6.

    Требование пункта: «Пункты технических требований должны иметь
    сквозную нумерацию». Проверяется буквально — что номера идут
    1, 2, 3… без пропусков и повторов.

    Если ТТ на чертеже нет вовсе, проверка не выполняется (None): по
    п. 6.1 технические требования приводят «при необходимости», их
    отсутствие само по себе не нарушение.
    """
    requirements = drawing.technical_requirements
    if not requirements:
        return None

    numbers = [r.number for r in requirements]
    expected_sequence = list(range(1, len(numbers) + 1))

    if numbers == expected_sequence:
        return GostRequirementCheck(
            standard_designation="ГОСТ Р 2.316-2023",
            clause_number="6.6",
            parameter_name="сквозная нумерация пунктов технических требований",
            status=GostCheckStatus.PASSED,
            actual_value=", ".join(str(n) for n in numbers),
            expected="1, 2, 3, … без пропусков",
            note="Нумерация пунктов ТТ сквозная.",
        )

    return GostRequirementCheck(
        standard_designation="ГОСТ Р 2.316-2023",
        clause_number="6.6",
        parameter_name="сквозная нумерация пунктов технических требований",
        status=GostCheckStatus.VIOLATED,
        actual_value=", ".join(str(n) for n in numbers),
        expected=", ".join(str(n) for n in expected_sequence),
        note=(
            "Нумерация пунктов ТТ не сквозная (пропуски, повторы или начало "
            "не с единицы). ГОСТ Р 2.316, п. 6.6 требует сквозной нумерации. "
            "Возможна также ошибка распознавания — проверьте оригинал."
        ),
    )


def check_material_designation(drawing: DrawingModel) -> GostRequirementCheck:
    """Обозначение материала в графе 3 по ГОСТ Р 2.109, п. 6.3.

    Проверяется не только факт заполнения (это делает check_title_block),
    но и соответствие форме записи: по п. 6.3 материал указывают
    «в соответствии с обозначением, установленным стандартами на материал
    или техническими условиями», то есть запись должна ссылаться на ГОСТ/ТУ.
    """
    material = drawing.title_block.material

    if not _is_field_filled(material):
        return GostRequirementCheck(
            standard_designation="ГОСТ Р 2.109-2023",
            clause_number="6.3",
            parameter_name="обозначение материала детали (графа 3)",
            status=GostCheckStatus.NEEDS_REVIEW,
            actual_value=None,
            expected="обозначение по стандарту на материал или ТУ",
            note=(
                "Материал не распознан в основной надписи. Для чертежа детали "
                "графа 3 должна быть заполнена (ГОСТ Р 2.109, п. 6.3); для "
                "сборочного чертежа — не требуется."
            ),
        )

    has_standard_reference = bool(
        re.search(r"(ГОСТ|ТУ|ОСТ|СТО)\s*[\dР]", material, flags=re.IGNORECASE)
    )

    if has_standard_reference:
        return GostRequirementCheck(
            standard_designation="ГОСТ Р 2.109-2023",
            clause_number="6.3",
            parameter_name="обозначение материала детали (графа 3)",
            status=GostCheckStatus.PASSED,
            actual_value=material,
            expected="обозначение по стандарту на материал или ТУ",
            note="Запись материала содержит ссылку на стандарт (ГОСТ/ТУ/ОСТ/СТО).",
        )

    return GostRequirementCheck(
        standard_designation="ГОСТ Р 2.109-2023",
        clause_number="6.3",
        parameter_name="обозначение материала детали (графа 3)",
        status=GostCheckStatus.NEEDS_REVIEW,
        actual_value=material,
        expected="обозначение по стандарту на материал или ТУ",
        note=(
            f"В записи материала «{material}» не найдена ссылка на стандарт "
            "(ГОСТ/ТУ/ОСТ/СТО). По ГОСТ Р 2.109, п. 6.3 материал указывают в "
            "соответствии с обозначением, установленным стандартами на "
            "материал или техническими условиями. Возможна также неполнота "
            "распознавания — проверьте оригинал."
        ),
    )


# Сортамент плоских заготовок: параметры ГОСТ 17232-2023, размеченные в
# базе как NUMERIC_LIMIT. Ключ — по какому размеру из обозначения
# заготовки сверять требование.
_PLATE_THICKNESS_MARKER = "толщина плиты"


def check_plate_blank_sortament(
    drawing: DrawingModel, numeric_requirements: tuple[GostNumericRequirement, ...]
) -> GostRequirementCheck | None:
    """Толщина плоской заготовки против сортамента ГОСТ 17232-2023.

    Сверяется ТОЛЬКО толщина. Ширина и длина в обозначении заготовки на
    чертеже детали — это размер вырезанной под деталь карточки
    («Плита Д16 А Т 35x80x80»), а не размер поставляемой плиты: по
    таблице 1 стандарта ширина начинается от 1000 мм, длина от 2000 мм,
    и сверка 80×80 с этими рядами дала бы заведомо ложное нарушение.
    Толщина же остаётся толщиной исходного листа при любой вырезке.

    Возвращает None, если заготовка не плоская, размеры не распознаны
    или в базе нет требования по толщине — молча «проходить» проверку,
    которая не выполнялась, нельзя.
    """
    blank = drawing.title_block.blank_designation
    if not blank or not is_plate_blank(blank):
        return None

    dimensions = extract_plate_dimensions_mm(blank)
    if dimensions is None:
        return None
    thickness_mm = dimensions[0]

    thickness_requirements = tuple(
        r
        for r in numeric_requirements
        if _PLATE_THICKNESS_MARKER in (r.parameter_name or "").lower()
        and r.comparison_op == "BETWEEN"
        and r.limit_value_min is not None
        and r.limit_value_max is not None
    )
    if not thickness_requirements:
        return None

    requirement = thickness_requirements[0]
    minimum = float(requirement.limit_value_min)
    maximum = float(requirement.limit_value_max)
    expected = f"от {minimum:g} до {maximum:g} {requirement.unit or 'мм'}"

    if minimum <= thickness_mm <= maximum:
        return GostRequirementCheck(
            standard_designation=requirement.standard_designation,
            clause_number=requirement.clause_number,
            parameter_name=requirement.parameter_name,
            status=GostCheckStatus.PASSED,
            actual_value=f"{thickness_mm:g} мм",
            expected=expected,
            note=(
                "Толщина заготовки входит в сортамент стандарта. Ширина и длина "
                "не сверялись: в обозначении заготовки чертежа детали это размер "
                "вырезанной карточки, а не поставляемой плиты."
            ),
        )

    return GostRequirementCheck(
        standard_designation=requirement.standard_designation,
        clause_number=requirement.clause_number,
        parameter_name=requirement.parameter_name,
        status=GostCheckStatus.VIOLATED,
        actual_value=f"{thickness_mm:g} мм",
        expected=expected,
        note=(
            f"Толщина заготовки {thickness_mm:g} мм вне сортамента "
            f"{requirement.standard_designation} ({expected}) — такая плита "
            "стандартом не выпускается. Проверьте обозначение заготовки или "
            "согласуйте другой вид проката."
        ),
    )


# Последовательность изложения ТТ по ГОСТ Р 2.316-2023, п. 6.5 —
# в терминах категорий из tt_categories.py. Порядок в кортеже = порядок
# в стандарте. Категории, для которых стандарт не задаёт места
# (process_sequence, inspection_testing и др.), в проверку не входят:
# домысливать за стандарт нельзя.
_TT_ORDER_BY_CATEGORY: tuple[tuple[str, str], ...] = (
    ("material", "требования к материалу"),
    ("heat_treatment", "термическая обработка и свойства материала"),
    ("chemical_thermal_treatment", "химико-термическая обработка"),
    ("unspecified_tolerances", "размеры и предельные отклонения"),
    ("form_position_tolerance", "геометрические допуски"),
    ("roughness", "качество поверхностей"),
    ("coating", "указания об отделке и покрытии"),
    ("marking", "указания о маркировании и клеймении"),
)


def check_technical_requirements_order(
    checks: tuple, 
) -> GostRequirementCheck | None:
    """Последовательность изложения пунктов ТТ (ГОСТ Р 2.316, п. 6.5).

    Стандарт требует группировать однородные требования и излагать их
    «по возможности в следующей последовательности» — формулировка
    рекомендательная, поэтому нарушение порядка даёт NEEDS_REVIEW, а не
    VIOLATED: расположить иначе стандарт не запрещает.

    Проверяются только те пункты, чья категория присутствует в перечне
    стандарта; остальные пропускаются, не сдвигая порядок.
    """
    order_index = {code: i for i, (code, _) in enumerate(_TT_ORDER_BY_CATEGORY)}
    titles = dict(_TT_ORDER_BY_CATEGORY)

    sequence = [
        (check.number, check.category)
        for check in checks
        if check.category in order_index
    ]
    if len(sequence) < 2:
        # Проверять последовательность не на чем.
        return None

    violations: list[str] = []
    for (prev_number, prev_category), (number, category) in zip(sequence, sequence[1:]):
        if order_index[category] < order_index[prev_category]:
            violations.append(
                f"п. {number} ({titles[category]}) стоит после "
                f"п. {prev_number} ({titles[prev_category]})"
            )

    actual = " → ".join(f"{n}:{titles[c]}" for n, c in sequence)
    if not violations:
        return GostRequirementCheck(
            standard_designation="ГОСТ Р 2.316-2023",
            clause_number="6.5",
            parameter_name="последовательность изложения технических требований",
            status=GostCheckStatus.PASSED,
            actual_value=actual,
            expected="; ".join(title for _, title in _TT_ORDER_BY_CATEGORY),
            note="Порядок групп требований соответствует рекомендованному стандартом.",
        )

    return GostRequirementCheck(
        standard_designation="ГОСТ Р 2.316-2023",
        clause_number="6.5",
        parameter_name="последовательность изложения технических требований",
        status=GostCheckStatus.NEEDS_REVIEW,
        actual_value=actual,
        expected="; ".join(title for _, title in _TT_ORDER_BY_CATEGORY),
        note=(
            "Порядок групп требований отличается от рекомендованного: "
            + "; ".join(violations)
            + ". Пункт 6.5 требует такой последовательности «по возможности», "
            "поэтому это не нарушение, а место для решения технолога."
        ),
    )

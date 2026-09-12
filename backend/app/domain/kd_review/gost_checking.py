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
    GostTitleBlockField,
)
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

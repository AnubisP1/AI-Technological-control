"""Сопоставление строки материала/заготовки с чертежа со справочником НСИ.

Формат материала на чертеже не всегда совпадает буква-в-букву с grade в
БД: чертёж даёт "45 ГОСТ 1050-2013" или "Сталь 12ХН3А ГОСТ 4543-2016",
а в справочнике grade хранится как "Сталь 45" — сравниваем по
нормализованному коду марки (без слова "Сталь"/пробелов) и по номеру
ГОСТ отдельно, чтобы не требовать точного текстового совпадения строки
целиком, но и не заявлять совпадение там, где марка не подтверждена.
"""

from __future__ import annotations

import re

from app.domain.kd_review.nsi_lookup_port import MaterialRecord, WorkpieceBlankRecord
from app.domain.kd_review.review_model import BlankCheck, MaterialCheck, MatchStatus
from app.domain.material_text import extract_blank_diameter_mm as _extract_blank_diameter_mm
from app.domain.material_text import extract_plate_thickness_mm
from app.domain.material_text import extract_gost_number as _extract_gost_number
from app.domain.material_text import extract_grade_part as _extract_grade_part
from app.domain.material_text import normalize_grade as _normalize_grade


def match_material(
    material_from_drawing: str | None,
    known_materials: tuple[MaterialRecord, ...],
    known_blanks: tuple[WorkpieceBlankRecord, ...] = (),
) -> MaterialCheck:
    if not material_from_drawing:
        return MaterialCheck(
            material_from_drawing=None,
            status=MatchStatus.NOT_FOUND,
            note="Материал не распознан на чертеже — сверка невозможна.",
        )

    grade_part = _normalize_grade(_extract_grade_part(material_from_drawing))
    gost_number = _extract_gost_number(material_from_drawing)

    # Полное совпадение (марка И ГОСТ) ищется по ВСЕЙ базе первым
    # приоритетом, не по первой попавшейся записи в порядке перебора —
    # реальный баг: если два материала в справочнике имеют один и тот же
    # ГОСТ (напр. 40Х и 12ХН3А оба по ГОСТ 4543-2016), запись, идущая
    # раньше по id, давала бы частичное совпадение и останавливала бы
    # поиск ещё до того, как дальше по списку нашлось бы точное
    # совпадение по марке.
    partial_match: MaterialRecord | None = None
    grade_match: MaterialRecord | None = None
    for record in known_materials:
        record_grade = _normalize_grade(record.grade)
        record_gost = _extract_gost_number(record.gost_standard or "")
        grade_matches = grade_part == record_grade
        gost_matches = gost_number is not None and gost_number == record_gost

        if grade_matches and gost_matches:
            return MaterialCheck(
                material_from_drawing=material_from_drawing,
                status=MatchStatus.MATCHED,
                matched_grade=record.grade,
                matched_gost=record.gost_standard,
                note="Материал найден в справочнике НСИ.",
            )
        if grade_matches and grade_match is None:
            grade_match = record
        if (grade_matches or gost_matches) and partial_match is None:
            partial_match = record

    # В основной надписи плиты может стоять ГОСТ на продукцию,
    # а в material — ГОСТ на химический состав марки. Это не конфликт,
    # если связанная заготовка НСИ подтверждает ту же марку и ГОСТ.
    if grade_match is not None and gost_number is not None:
        product_standard_confirmed = any(
            _normalize_grade(blank.material_grade or "") == grade_part
            and _extract_gost_number(blank.gost_standard or "") == gost_number
            for blank in known_blanks
        )
        if product_standard_confirmed:
            return MaterialCheck(
                material_from_drawing=material_from_drawing,
                status=MatchStatus.PARTIAL_MATCH,
                matched_grade=grade_match.grade,
                matched_gost=grade_match.gost_standard,
                note=(
                    "Марка найдена в НСИ, а ссылка ведёт на стандарт "
                    "продукции/сортамента. Полное совпадение возможно после "
                    "проверки плакировки и состояния по ГОСТ."
                ),
            )

    if partial_match is not None:
        return MaterialCheck(
            material_from_drawing=material_from_drawing,
            status=MatchStatus.PARTIAL_MATCH,
            matched_grade=partial_match.grade,
            matched_gost=partial_match.gost_standard,
            note=(
                "Частичное совпадение с записью НСИ "
                f"({partial_match.grade}, {partial_match.gost_standard}) — "
                "марка и ГОСТ распознаны из разных записей справочника, "
                "требуется проверка технологом."
            ),
        )

    return MaterialCheck(
        material_from_drawing=material_from_drawing,
        status=MatchStatus.NOT_FOUND,
        note="Материал не найден в справочнике НСИ — доступность не подтверждена.",
    )


def match_blank(
    blank_from_drawing: str | None, known_blanks: tuple[WorkpieceBlankRecord, ...]
) -> BlankCheck:
    if not blank_from_drawing:
        return BlankCheck(
            blank_from_drawing=None,
            status=MatchStatus.NOT_FOUND,
            note="Заготовка не распознана на чертеже — сверка невозможна.",
        )

    gost_number = _extract_gost_number(blank_from_drawing)
    diameter_match = re.search(r"[ØO]\s*(\d+(?:[.,]\d+)?)", blank_from_drawing, re.IGNORECASE)
    drawing_diameter = (
        float(diameter_match.group(1).replace(",", "."))
        if diameter_match
        else _extract_blank_diameter_mm(blank_from_drawing)
    )

    # Плоский прокат сверяется по ТОЛЩИНЕ, а не по диаметру: у листа и
    # плиты диаметра нет, и сообщение «диаметр в НСИ отсутствует» для них
    # бессмысленно. Ширина и длина не сверяются — в чертеже детали это
    # размер вырезанной карточки, а не поставляемого листа
    # (см. gost_checking.check_plate_blank_sortament).
    drawing_thickness = extract_plate_thickness_mm(blank_from_drawing)

    for record in known_blanks:
        record_gost = _extract_gost_number(record.gost_standard or "")
        gost_matches = gost_number is not None and gost_number == record_gost
        if not gost_matches:
            continue

        if (
            drawing_thickness is not None
            and record.thickness_mm is not None
            and abs(drawing_thickness - record.thickness_mm) < 0.5
        ):
            return BlankCheck(
                blank_from_drawing=blank_from_drawing,
                status=MatchStatus.MATCHED,
                matched_designation=record.designation,
                note="Заготовка найдена в справочнике НСИ (толщина совпала).",
            )

        if drawing_thickness is not None:
            thickness_note = (
                f"толщина по чертежу ({drawing_thickness:g} мм) не совпадает со "
                f"справочной ({record.thickness_mm:g} мм)"
                if record.thickness_mm is not None
                else "конкретный типоразмер (толщина) в НСИ отсутствует"
            )
            return BlankCheck(
                blank_from_drawing=blank_from_drawing,
                status=MatchStatus.PARTIAL_MATCH,
                matched_designation=record.designation,
                note=(
                    f"ГОСТ заготовки найден в справочнике ({record.designation}), "
                    f"но {thickness_note} — "
                    "требуется добавить в справочник или уточнить у технолога."
                ),
            )

        if (
            drawing_diameter is not None
            and record.diameter_mm is not None
            and abs(drawing_diameter - record.diameter_mm) < 0.5
        ):
            return BlankCheck(
                blank_from_drawing=blank_from_drawing,
                status=MatchStatus.MATCHED,
                matched_designation=record.designation,
                note="Заготовка найдена в справочнике НСИ (типоразмер совпал).",
            )
        diameter_note = (
            f"диаметр по чертежу ({drawing_diameter:g} мм) не совпадает со "
            f"справочным ({record.diameter_mm:g} мм)"
            if drawing_diameter is not None and record.diameter_mm is not None
            else "конкретный типоразмер (диаметр) в НСИ отсутствует"
        )
        return BlankCheck(
            blank_from_drawing=blank_from_drawing,
            status=MatchStatus.PARTIAL_MATCH,
            matched_designation=record.designation,
            note=(
                f"ГОСТ заготовки найден в справочнике ({record.designation}), "
                f"но {diameter_note} — "
                "требуется добавить в справочник или уточнить у технолога."
            ),
        )

    return BlankCheck(
        blank_from_drawing=blank_from_drawing,
        status=MatchStatus.NOT_FOUND,
        note="Заготовка не найдена в справочнике НСИ — доступность не подтверждена.",
    )

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
from app.domain.material_text import extract_gost_number as _extract_gost_number
from app.domain.material_text import extract_grade_part as _extract_grade_part
from app.domain.material_text import normalize_grade as _normalize_grade


def match_material(
    material_from_drawing: str | None, known_materials: tuple[MaterialRecord, ...]
) -> MaterialCheck:
    if not material_from_drawing:
        return MaterialCheck(
            material_from_drawing=None,
            status=MatchStatus.NOT_FOUND,
            note="Материал не распознан на чертеже — сверка невозможна.",
        )

    grade_part = _normalize_grade(_extract_grade_part(material_from_drawing))
    gost_number = _extract_gost_number(material_from_drawing)

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
        if grade_matches or gost_matches:
            return MaterialCheck(
                material_from_drawing=material_from_drawing,
                status=MatchStatus.PARTIAL_MATCH,
                matched_grade=record.grade,
                matched_gost=record.gost_standard,
                note=(
                    "Частичное совпадение с записью НСИ "
                    f"({record.grade}, {record.gost_standard}) — "
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

    for record in known_blanks:
        record_gost = _extract_gost_number(record.gost_standard or "")
        gost_matches = gost_number is not None and gost_number == record_gost
        if not gost_matches:
            continue

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

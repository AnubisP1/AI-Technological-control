"""Общие функции разбора строки материала/ГОСТ, как она встречается на
чертежах ("45 ГОСТ 1050-2013", "Сталь 12ХН3А ГОСТ 4543-2016") — формат
систематически отличается от `grade` в справочнике НСИ ("Сталь 45").
Используется и сверкой КД с НСИ (Модуль 1.2, kd_review), и автоподбором
техпроцесса (Модуль 1.3, process_planning) — вынесено сюда, чтобы не
дублировать нормализацию марки между модулями.
"""

from __future__ import annotations

import re

_RE_GOST_NUMBER = re.compile(r"ГОСТ\s*([\d.\-]+)", re.IGNORECASE)
_RE_STRIP_STEEL_PREFIX = re.compile(r"^Сталь\s+", re.IGNORECASE)


def normalize_grade(text: str) -> str:
    """Убирает слово 'Сталь' и пробелы, приводит к верхнему регистру —
    "Сталь 45" и "45" должны сравниваться как одна и та же марка."""
    without_prefix = _RE_STRIP_STEEL_PREFIX.sub("", text)
    return re.sub(r"\s+", "", without_prefix).upper()


def extract_gost_number(text: str) -> str | None:
    match = _RE_GOST_NUMBER.search(text)
    return match.group(1) if match else None


def extract_grade_part(material_text: str) -> str:
    """Отрезает от строки материала часть с ГОСТ, оставляя только марку —
    'Сталь 12ХН3А ГОСТ 4543-2016' -> 'Сталь 12ХН3А'."""
    gost_pos = material_text.upper().find("ГОСТ")
    return material_text[:gost_pos].strip() if gost_pos != -1 else material_text.strip()

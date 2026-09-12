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
# Диаметр проката текстом сразу после названия профиля ("Круг 67 ГОСТ...",
# "Пруток 40 ГОСТ...") — реальный формат обозначения заготовки на
# чертежах проекта (см. stamp_extraction.py, _RE_BLANK_LINE), отличается
# от формата с символом Ø, который ищется отдельно в match_blank.
_RE_BLANK_PROFILE_DIAMETER = re.compile(
    r"^(?:Круг|Пруток|Труба)\s+(\d+(?:[.,]\d+)?)", re.IGNORECASE
)
# Плоский сортамент: «Плита Д16 А Т 35x80x80 ГОСТ 17232-2023» — размеры
# идут тройкой толщина×ширина×длина. Разделителем на чертежах бывает и
# латинская «x», и русская «х», и знак «×». Между размерами и буквами
# состояния/точности возможен суффикс «П» (повышенная точность по
# толщине, ГОСТ 17232-2023 п. 3.1) — «20Пх1200x3000», поэтому он
# допускается сразу после первого числа и в захват не входит.
_RE_PLATE_DIMENSIONS = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*[ПP]?\s*[xх×]\s*(\d+(?:[.,]\d+)?)\s*[xх×]\s*(\d+(?:[.,]\d+)?)",
    re.IGNORECASE,
)
_RE_PLATE_PROFILE = re.compile(r"^(?:Плита|Лист|Полоса)\b", re.IGNORECASE)


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


def extract_blank_diameter_mm(blank_designation: str) -> float | None:
    """Извлекает диаметр проката из обозначения заготовки чертежа
    ('Круг 67 ГОСТ 2590-2006' -> 67.0) — нужен для расчёта режимов
    резания (глубина/скорость зависят от диаметра заготовки). Не
    предполагает символ Ø (реальные чертежи проекта его не используют
    в этом поле, см. stamp_extraction.py) — если профиль не круглый
    (Лист/Полоса) или формат не распознан, возвращает None, не
    подставляет произвольное число."""
    match = _RE_BLANK_PROFILE_DIAMETER.search(blank_designation.strip())
    return float(match.group(1).replace(",", ".")) if match else None


def is_plate_blank(blank_designation: str) -> bool:
    """Плоский ли это сортамент («Плита ...», «Лист ...», «Полоса ...»).
    Отличается от круглого проката тем, что размер задаётся тройкой
    толщина×ширина×длина, а не диаметром."""
    return bool(_RE_PLATE_PROFILE.match(blank_designation.strip()))


def extract_plate_dimensions_mm(
    blank_designation: str,
) -> tuple[float, float, float] | None:
    """Извлекает (толщина, ширина, длина) из обозначения плоской
    заготовки: «Плита Д16 А Т 35x80x80 ГОСТ 17232-2023» -> (35, 80, 80).

    Порядок размеров — по ГОСТ 17232-2023, п. 4.2.8 (пример условного
    обозначения «Плита Д16 А Т 20x1200x3000»): толщина, ширина, длина.
    Возвращает None, если тройка размеров не распознана — подставлять
    произвольные числа нельзя, от них зависит вердикт проверки.
    """
    match = _RE_PLATE_DIMENSIONS.search(blank_designation)
    if match is None:
        return None
    return tuple(float(g.replace(",", ".")) for g in match.groups())  # type: ignore[return-value]

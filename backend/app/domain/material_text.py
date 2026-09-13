"""Общие функции разбора строки материала/ГОСТ, как она встречается на
чертежах ("45 ГОСТ 1050-2013", "Сталь 12ХН3А ГОСТ 4543-2016") — формат
систематически отличается от `grade` в справочнике НСИ ("Сталь 45").
Используется и сверкой КД с НСИ (Модуль 1.2, kd_review), и автоподбором
техпроцесса (Модуль 1.3, process_planning) — вынесено сюда, чтобы не
дублировать нормализацию марки между модулями.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

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
# Полный перечень профилей сортамента, встречающихся в графе 3 реальных
# чертежей. Шире, чем _RE_PLATE_PROFILE (только плоский прокат) и чем
# _RE_BLANK_PROFILE_DIAMETER (только круглый) — используется там, где
# нужно опознать саму строку заготовки независимо от вида профиля.
BLANK_PROFILE_ALTERNATION = (
    "Круг|Лист|Плита|Пруток|Полоса|Труба|Уголок|Профиль|Швеллер|Лента|"
    "Проволока|Шестигранник|Квадрат"
)
_RE_LEADING_PROFILE = re.compile(rf"^(?:{BLANK_PROFILE_ALTERNATION})\b\.?", re.IGNORECASE)
# Токен, состоящий только из размеров: «35x80x80», «10х15х1,5», «2».
_RE_SIZE_TOKEN = re.compile(r"^[\d.,]+(?:[xх×][\d.,]+)*$", re.IGNORECASE)
# Обозначения плакировки/состояния материала/точности по ГОСТ 17232-2023
# п. 3.1 — отдельными токенами («Д16 А Т 35x80x80») или слитно («Д16 АТ»).
# Это характеристики поставки, а не часть марки.
_TEMPER_TOKENS = frozenset(
    {
        "А", "Б", "М", "Н", "Н1", "Н2", "Т", "Т1", "П",
        "АТ", "АТ1", "АМ", "БТ", "БТ1", "БМ",
    }
)

_PLATING_TOKENS = frozenset({"А", "Б"})
_MATERIAL_STATE_TOKENS = frozenset({"М", "Н", "Н1", "Н2", "Т", "Т1"})
_COMBINED_PLATE_TOKENS: dict[str, tuple[str, str]] = {
    "АТ": ("А", "Т"),
    "АТ1": ("А", "Т1"),
    "АМ": ("А", "М"),
    "БТ": ("Б", "Т"),
    "БТ1": ("Б", "Т1"),
    "БМ": ("Б", "М"),
}


@dataclass(frozen=True)
class PlateMaterialAttributes:
    """Структура обозначения плиты по ГОСТ 17232-2023."""

    grade: str
    plating: str | None = None
    material_state: str | None = None


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
    head = material_text[:gost_pos].strip() if gost_pos != -1 else material_text.strip()
    tokens = head.split()
    # Отдельные суффиксы — атрибуты поставки, а не часть марки.
    # Слитный суффикс внутри самой марки при этом не изменяется.
    while len(tokens) > 1 and tokens[-1].upper() in _TEMPER_TOKENS:
        tokens.pop()
    return " ".join(tokens)


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


def extract_plate_material_attributes(
    blank_designation: str,
) -> PlateMaterialAttributes | None:
    """Извлекает марку, плакировку и состояние материала плиты.

    Понимает как нормативную запись с раздельными «А Т», так и слитное
    OCR-прочтение «АТ».
    """
    if not is_plate_blank(blank_designation):
        return None

    gost_match = _RE_GOST_NUMBER.search(blank_designation)
    head = blank_designation[: gost_match.start()] if gost_match else blank_designation
    head = _RE_LEADING_PROFILE.sub("", head.strip(), count=1).strip()
    dimensions = _RE_PLATE_DIMENSIONS.search(head)
    if dimensions is not None:
        head = head[: dimensions.start()].strip()
    else:
        # У листа может быть один размер после марки.
        head = re.sub(r"\s+\d+(?:[.,]\d+)?\s*$", "", head)

    tokens = [token.strip(".,;").upper() for token in head.split() if token.strip(".,;")]
    grade_index = next(
        (
            index
            for index, token in enumerate(tokens)
            if re.search(r"[A-ZА-ЯЁ]", token)
            and token not in _TEMPER_TOKENS
        ),
        None,
    )
    if grade_index is None:
        return None

    grade = tokens[grade_index]
    modifiers = tokens[grade_index + 1 :]
    if len(modifiers) == 1 and modifiers[0] in _COMBINED_PLATE_TOKENS:
        modifiers = list(_COMBINED_PLATE_TOKENS[modifiers[0]])

    plating = next((token for token in modifiers if token in _PLATING_TOKENS), None)
    material_state = next(
        (token for token in modifiers if token in _MATERIAL_STATE_TOKENS), None
    )
    return PlateMaterialAttributes(
        grade=grade,
        plating=plating,
        material_state=material_state,
    )


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


def extract_material_from_blank_designation(blank_designation: str) -> str | None:
    """Извлекает обозначение материала из совмещённой записи графы 3.

    Серии чертежей (напр. МВАУ) пишут профиль и марку одной строкой:
    «Лист Д16Т 2 ГОСТ 21631-2023», «Плита Д16 АТ 35x80x80 ГОСТ 17232-2023»,
    «Лист 2 Д16 ГОСТ 21631-2019». Такая строка несёт ОБА факта сразу —
    и заготовку, и материал, поэтому она разбирается дважды, разными
    функциями, а не «или то, или другое».

    Возвращает None, если марку выделить нельзя:
    - нет ссылки на стандарт («Лист Д16») — по ГОСТ Р 2.109 п. 6.3
      материал указывают с обозначением стандарта, одна марка
      обозначением материала не является;
    - в записи вообще нет марки («Круг 67 ГОСТ 2590-2006»,
      «Уголок 10х15х1,5 ГОСТ 22233-2018») — там только типоразмер.
    Додумывать марку в этих случаях нельзя: она берётся из отдельной
    строки штампа другим путём разбора.
    """
    text = blank_designation.strip()
    gost_match = _RE_GOST_NUMBER.search(text)
    if gost_match is None:
        return None

    head = text[: gost_match.start()]
    head = _RE_LEADING_PROFILE.sub("", head, count=1)

    plate_attributes = extract_plate_material_attributes(text)
    if plate_attributes is not None:
        parts = [plate_attributes.grade]
        if plate_attributes.plating is not None:
            parts.append(plate_attributes.plating)
        if plate_attributes.material_state is not None:
            parts.append(plate_attributes.material_state)
        return f"{' '.join(parts)} ГОСТ {gost_match.group(1)}"

    for token in head.split():
        cleaned = token.strip(".,;")
        if not cleaned:
            continue
        if _RE_SIZE_TOKEN.match(cleaned):
            continue
        if cleaned.upper() in _TEMPER_TOKENS:
            continue
        if not re.search(r"[A-Za-zА-Яа-яЁё]", cleaned):
            continue
        return f"{cleaned} ГОСТ {gost_match.group(1)}"

    return None


def extract_plate_thickness_mm(blank_designation: str) -> float | None:
    """Толщина плоской заготовки в миллиметрах.

    Два формата записи на реальных чертежах:
    - тройка размеров «Плита Д16 АТ 35x80x80» -> первое число (толщина);
    - одиночное число «Лист Д16Т 2 ГОСТ 21631-2023» -> оно и есть толщина
      (ширина и длина для листа в чертеже детали не указываются).

    Возвращает None, если заготовка не плоская или число не найдено.
    """
    if not is_plate_blank(blank_designation):
        return None

    dimensions = extract_plate_dimensions_mm(blank_designation)
    if dimensions is not None:
        return dimensions[0]

    # Одиночное число до ссылки на стандарт. Марку («Д16Т», «АМг2»)
    # пропускаем: цифры внутри марки не являются размером.
    gost_match = _RE_GOST_NUMBER.search(blank_designation)
    head = blank_designation[: gost_match.start()] if gost_match else blank_designation
    head = _RE_LEADING_PROFILE.sub("", head.strip(), count=1)
    for token in head.split():
        cleaned = token.strip(".,;")
        if re.fullmatch(r"\d+(?:[.,]\d+)?", cleaned):
            return float(cleaned.replace(",", "."))
    return None

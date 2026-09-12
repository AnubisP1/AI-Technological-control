"""Общая логика извлечения основной надписи (ГОСТ 2.104) и технических
требований из уже полученного списка текстовых строк с координатами —
не зависит от того, откуда эти строки взялись: из текстового слоя PDF
(PdfDrawingParser) или из результата OCR сканированной страницы
(OcrDrawingParser). Вынесено отдельно, чтобы не дублировать
позиционную эвристику штампа между двумя источниками текста.
"""

from __future__ import annotations

import re

from app.domain.cad.drawing_model import TechnicalRequirement, TitleBlockFields
from app.domain.material_text import (
    BLANK_PROFILE_ALTERNATION,
    extract_material_from_blank_designation,
)

Line = tuple[float, float, float, float, str]  # x0, y0, x1, y1, text

# Штамп ГОСТ 2.104 форма 1 занимает нижний правый угол листа — эвристика
# по доле площади листа, устойчивая к разным форматам (A4/A3/A2/A1).
STAMP_X_FRACTION = 0.66
STAMP_Y_FRACTION = 0.78

_LABEL_ROW_TOLERANCE_PX = 6
# Допуски склейки перенесённой строки пункта ТТ (в единицах PDF, 1/72").
_CONTINUATION_X_TOLERANCE_PX = 4
_CONTINUATION_MAX_LINE_GAP_PX = 24

# Номер пункта ТТ: точка после номера НЕОБЯЗАТЕЛЬНА. Реальные серии
# чертежей пишут и «1. Текст», и «1 Текст» (по корпусу МВАУ: 125 файлов
# с точкой, 145 без неё). Ограничение двумя цифрами и позиционный фильтр
# ниже не дают спутать пункт ТТ со строкой спецификации.
_RE_TECH_REQUIREMENT = re.compile(r"^\s*(\d{1,2})[.)]?\s*(.+?)\.?\s*$")
# Технические требования располагают над основной надписью, то есть в
# правой части листа. Замеры реальных чертежей: ТТ начинаются на 0.53,
# 0.68 и 0.84 ширины листа, строки спецификаций — на 0.16. Порог 0.5
# разделяет их с запасом; повышать его нельзя — на 0.6 теряются ТТ
# чертежа «Вал» (0.53).
TT_X_FRACTION = 0.5
# Строка спецификации начинается с обозначения КД («МВАУ.104759.001-01…»)
# — вторая линия защиты, если позиционный фильтр окажется неточен.
_RE_KD_DESIGNATION_START = re.compile(r"^[А-ЯЁ]{2,}\.\d")
# Нижняя полоса листа — сама таблица основной надписи. Пункты ТТ лежат
# НАД ней, а внутри неё нумерованной выглядит, например, строка материала
# «45 ГОСТ 1050-2013» (номер марки читается как номер пункта). Граница
# ниже STAMP_Y_FRACTION: у «Шестерни» пункты ТТ доходят до 0.82 листа,
# то есть формально заходят в полосу штампа по этой доле.
TT_STAMP_Y_FRACTION = 0.90
# Марка может содержать строчную кириллицу («АМг2») и точку («Д16.Т»);
# первый символ остаётся заглавным/цифрой, чтобы не цеплять обычный текст.
_RE_MATERIAL_LINE = re.compile(
    r"^[0-9A-ZА-ЯЁ][0-9A-Za-zА-Яа-яЁё.\-]*\s+ГОСТ\s+[\d.\-]+$"
)
_RE_BLANK_LINE = re.compile(rf"^(?:{BLANK_PROFILE_ALTERNATION})\s+", re.IGNORECASE)
# Обозначение группы поковки по ГОСТ 8479-70 ("2. Гр. III ГОСТ 8479-70") —
# встречается не в штампе (заготовка там указывается только для проката
# стандартного профиля, см. _RE_BLANK_LINE), а в технических требованиях
# чертежа как пронумерованный пункт, как в реальном тестовом чертеже
# "Шестерня от конической передачи..." (КД для тестов/Детали из
# металла/2. Тестовая деталь металл/) — заготовка-поковка не даёт
# диаметра/типового профиля, поэтому здесь используется как отдельный
# источник blank_designation. Необязательный префикс "N. " — номер
# пункта технических требований, не часть самого обозначения.
_RE_FORGING_GROUP_LINE = re.compile(r"^(?:\d+\.\s*)?(Гр\.?\s*[IVX]+\s+ГОСТ\s+[\d.\-]+)", re.IGNORECASE)
_RE_DATE = re.compile(r"^\d{2}\.\d{2}\.\d{4}$")

KNOWN_LABELS = {
    "Лит.", "Масса", "Масштаб", "Дата", "Лист", "Листов", "Формат",
    "Копировал", "Изм.", "№ докум.", "Подп.", "Разраб.", "Пров.",
    "Т.контр.", "Н.контр.", "Утв.", "Подп. и дата",
}


def extract_title_block(lines: list[Line], page_width: float, page_height: float) -> TitleBlockFields:
    stamp_x = page_width * STAMP_X_FRACTION
    stamp_y = page_height * STAMP_Y_FRACTION
    stamp_lines = [ln for ln in lines if ln[0] >= stamp_x and ln[1] >= stamp_y]

    scale = _value_right_of_label(stamp_lines, "Масштаб")
    sheet_format = _value_right_of_label(stamp_lines, "Формат")
    mass = _value_right_of_label(stamp_lines, "Масса")
    designation = _designation(stamp_lines)
    part_name = _part_name(stamp_lines, designation)
    # Заготовка определяется ДО материала: у совмещённой записи графы 3
    # («Лист Д16Т 2 ГОСТ 21631-2023») это одна и та же строка, из которой
    # затем извлекается марка. Поковка («Гр. III ГОСТ 8479-70») в такой
    # разбор не идёт — там типоразмер группы, а не марка.
    rolled_blank = _first_matching(stamp_lines, _RE_BLANK_LINE)
    blank_designation = rolled_blank or _first_matching_group(lines, _RE_FORGING_GROUP_LINE)
    material = _material(stamp_lines, rolled_blank)

    return TitleBlockFields(
        designation=designation,
        part_name=part_name,
        material=material,
        blank_designation=blank_designation,
        scale=scale,
        sheet_format=sheet_format,
        mass=mass,
    )


def extract_technical_requirements(
    lines: list[Line], page_width: float, page_height: float
) -> tuple[TechnicalRequirement, ...]:
    """Технические требования — пронумерованный список над основной
    надписью (см. dev/QUESTIONS.md №4).

    Разбор ПОЗИЦИОННЫЙ, а не только по тексту: точка после номера
    необязательна, а значит одного регулярного выражения недостаточно —
    строки спецификаций («1 МВАУ.104759.001-01.140.001 Обшивка»)
    нумеруются точно так же и превратились бы в десятки фиктивных
    пунктов. Разделяет их положение на листе (см. TT_X_FRACTION).

    Нумерация НЕ проверяется на непрерывность: пропуски и повторы — это
    нарушение ГОСТ Р 2.316 п. 6.6, о котором обязана сообщить проверка
    check_technical_requirements_numbering(). Молча пропускать такой
    пункт значило бы и скрыть его от технолога, и подавить ту самую
    находку, которая должна о нём сообщить.
    """
    x_threshold = page_width * TT_X_FRACTION
    y_limit = page_height * TT_STAMP_Y_FRACTION
    candidates = sorted(
        (ln for ln in lines if ln[0] >= x_threshold and ln[1] < y_limit),
        key=lambda ln: (ln[1], ln[0]),
    )

    requirements: list[TechnicalRequirement] = []
    # Продолжение перенесённого пункта идёт без номера и с той же левой
    # границы, что и его первая строка («2 Фюзеляж поз. 2 крепить … /
    # и Гайку М8 … из состава крыла»). Без склейки классификатор ТТ
    # получил бы обрубок фразы.
    current_x0: float | None = None
    current_y1: float | None = None

    for x0, _y0, _x1, y1, text in candidates:
        stripped = text.strip()
        if not stripped or stripped in KNOWN_LABELS:
            continue

        match = _RE_TECH_REQUIREMENT.match(stripped)
        # Достаточно одной буквы: настоящие пункты бывают почти целиком
        # числовыми («262.....311 HB», «H12, h12, ± IT12|2»). От ячеек
        # таблиц вида «1 6» защищает позиционный фильтр, а не длина слова.
        is_numbered = match is not None and bool(
            re.search(r"[A-Za-zА-Яа-яЁё]", match.group(2))
        )
        if is_numbered and _RE_KD_DESIGNATION_START.match(match.group(2).strip()):
            is_numbered = False

        if is_numbered:
            number = int(match.group(1))
            # Блок ТТ начинается с пункта 1. Всё нумерованное выше него —
            # выноски и обозначения на поле чертежа («14. JS9(±0,0215)»,
            # «8. -B»), которые тоже начинаются с числа. Отсчёт ведём от
            # первой встреченной единицы; далее номера принимаются как
            # есть (разрывы — предмет проверки ГОСТ Р 2.316 п. 6.6,
            # см. докстроку).
            if not requirements and number != 1:
                continue
            requirements.append(
                TechnicalRequirement(number=number, text=match.group(2).strip())
            )
            current_x0, current_y1 = x0, y1
            continue

        if (
            requirements
            and current_x0 is not None
            and current_y1 is not None
            and abs(x0 - current_x0) < _CONTINUATION_X_TOLERANCE_PX
            and 0 <= y1 - current_y1 < _CONTINUATION_MAX_LINE_GAP_PX
            and re.search(r"[A-Za-zА-Яа-яЁё]{3}", stripped)
            and not _RE_TECH_REQUIREMENT.match(stripped)
        ):
            previous = requirements[-1]
            merged = f"{previous.text} {stripped.rstrip('.')}".strip()
            requirements[-1] = TechnicalRequirement(number=previous.number, text=merged)
            current_y1 = y1

    return tuple(requirements)


def _value_right_of_label(lines: list[Line], label: str) -> str | None:
    label_line = next((ln for ln in lines if ln[4] == label), None)
    if label_line is None:
        return None
    label_x0, label_y0, label_x1, label_y1 = label_line[:4]
    label_y_center = (label_y0 + label_y1) / 2

    same_row = [
        ln
        for ln in lines
        if ln[4] != label
        and ln[4] not in KNOWN_LABELS
        and ln[0] > label_x1
        and abs((ln[1] + ln[3]) / 2 - label_y_center) < _LABEL_ROW_TOLERANCE_PX
    ]
    if same_row:
        same_row.sort(key=lambda ln: ln[0])
        return same_row[0][4]

    below = [
        ln
        for ln in lines
        if ln[4] != label and ln[1] >= label_y1 - 1 and ln[0] < label_x1 and ln[2] > label_x0
    ]
    if below:
        below.sort(key=lambda ln: ln[1])
        return below[0][4]
    return None


def _designation(lines: list[Line]) -> str | None:
    candidates = [
        ln
        for ln in lines
        if ln[4] not in KNOWN_LABELS
        and " " not in ln[4]
        and not _RE_DATE.match(ln[4])
        and re.search(r"[A-ZА-ЯЁ0-9]", ln[4])
    ]
    if not candidates:
        return None
    candidates.sort(key=lambda ln: ln[1])
    return candidates[0][4]


def _part_name(lines: list[Line], designation: str | None) -> str | None:
    text_lines = [
        ln
        for ln in lines
        if ln[4] not in KNOWN_LABELS
        and ln[4] != designation
        and re.fullmatch(r"[A-ЯЁA-Za-zа-яё .,]+", ln[4])
    ]
    starters = [ln for ln in text_lines if ln[4][:1].isupper()]
    if not starters:
        return None
    starters.sort(key=lambda ln: ln[1])
    text_lines.sort(key=lambda ln: ln[1])
    start = starters[0]
    remaining = [ln for ln in text_lines if ln[1] > start[1]]
    collected = [start[4]]
    prev_y1 = start[3]
    start_x0, start_x1 = start[0], start[2]
    for ln in remaining:
        x0, _, x1, _ = ln[:4]
        overlaps_column = x0 < start_x1 and x1 > start_x0
        if ln[1] - prev_y1 >= 20:
            break
        if overlaps_column:
            collected.append(ln[4])
            prev_y1 = ln[3]
            start_x0, start_x1 = min(start_x0, x0), max(start_x1, x1)
    return " ".join(collected)


def _material(lines: list[Line], rolled_blank: str | None = None) -> str | None:
    """Материал из основной надписи. Три яруса разбора, порядок значим —
    более частные формы проверяются раньше совмещённой записи."""
    # 1. Отдельная строка «МАРКА ГОСТ N» («45 ГОСТ 1050-2013»).
    single = _first_matching(lines, _RE_MATERIAL_LINE)
    if single:
        return single

    # 2. Марка и стандарт разнесены по двум строкам («Сталь 12ХН3А» / «ГОСТ 4543-2016»).
    grade_lines = [ln for ln in lines if re.match(r"^Сталь\s+\S+", ln[4], re.IGNORECASE)]
    gost_lines = [ln for ln in lines if re.match(r"^ГОСТ\s+[\d.\-]+$", ln[4])]
    for grade_ln in grade_lines:
        for gost_ln in gost_lines:
            if abs(gost_ln[1] - grade_ln[3]) < 25 and abs(gost_ln[0] - grade_ln[0]) < 30:
                return f"{grade_ln[4]} {gost_ln[4]}"

    # 3. Совмещённая запись профиля и марки одной строкой. Последний ярус:
    # срабатывает, только если материал не найден двумя точными способами
    # выше, и возвращает None, если марки в записи нет вовсе.
    if rolled_blank:
        return extract_material_from_blank_designation(rolled_blank)
    return None


def _first_matching(lines: list[Line], pattern: re.Pattern) -> str | None:
    for ln in lines:
        if pattern.match(ln[4]):
            return ln[4]
    return None


def _first_matching_group(lines: list[Line], pattern: re.Pattern) -> str | None:
    """Как _first_matching, но возвращает первую захватывающую группу,
    а не всю строку — для паттернов с посторонним префиксом (напр.
    номер пункта технических требований "2. Гр. III ГОСТ 8479-70",
    где "2. " не часть искомого обозначения)."""
    for ln in lines:
        match = pattern.match(ln[4])
        if match:
            return match.group(1)
    return None

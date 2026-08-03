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

Line = tuple[float, float, float, float, str]  # x0, y0, x1, y1, text

# Штамп ГОСТ 2.104 форма 1 занимает нижний правый угол листа — эвристика
# по доле площади листа, устойчивая к разным форматам (A4/A3/A2/A1).
STAMP_X_FRACTION = 0.66
STAMP_Y_FRACTION = 0.78

_LABEL_ROW_TOLERANCE_PX = 6

_RE_TECH_REQUIREMENT = re.compile(r"^\s*(\d+)\.\s*(.+?)\.?\s*$")
_RE_MATERIAL_LINE = re.compile(r"^[A-ЯЁ0-9ХГТ]+\s+ГОСТ\s+[\d.\-]+$")
_RE_BLANK_LINE = re.compile(r"^(Круг|Лист|Пруток|Полоса|Труба)\s+", re.IGNORECASE)
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
    material = _material(stamp_lines)
    blank_designation = _first_matching(stamp_lines, _RE_BLANK_LINE) or _first_matching_group(
        lines, _RE_FORGING_GROUP_LINE
    )

    return TitleBlockFields(
        designation=designation,
        part_name=part_name,
        material=material,
        blank_designation=blank_designation,
        scale=scale,
        sheet_format=sheet_format,
        mass=mass,
    )


def extract_technical_requirements(raw_text: str) -> tuple[TechnicalRequirement, ...]:
    """Технические требования — пронумерованный список над штампом
    (см. dev/QUESTIONS.md №4). Отсеивает ложные срабатывания вида дат/
    размеров, случайно похожих на 'число.текст'."""
    requirements: list[TechnicalRequirement] = []
    seen_numbers: set[int] = set()
    for line in raw_text.splitlines():
        match = _RE_TECH_REQUIREMENT.match(line)
        if not match:
            continue
        number = int(match.group(1))
        text = match.group(2).strip()
        if not re.search(r"[A-ZА-ЯЁa-zа-яё]", text):
            continue
        expected_next = len(seen_numbers) + 1
        if number != expected_next:
            continue
        seen_numbers.add(number)
        requirements.append(TechnicalRequirement(number=number, text=text))
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


def _material(lines: list[Line]) -> str | None:
    single = _first_matching(lines, _RE_MATERIAL_LINE)
    if single:
        return single

    grade_lines = [ln for ln in lines if re.match(r"^Сталь\s+\S+", ln[4], re.IGNORECASE)]
    gost_lines = [ln for ln in lines if re.match(r"^ГОСТ\s+[\d.\-]+$", ln[4])]
    for grade_ln in grade_lines:
        for gost_ln in gost_lines:
            if abs(gost_ln[1] - grade_ln[3]) < 25 and abs(gost_ln[0] - grade_ln[0]) < 30:
                return f"{grade_ln[4]} {gost_ln[4]}"
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

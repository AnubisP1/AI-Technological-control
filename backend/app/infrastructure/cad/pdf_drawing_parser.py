"""Парсер чертежа из PDF с текстовым слоем (PyMuPDF).

Извлекает основную надпись (штамп, ГОСТ 2.104) и технические требования.
Работает только для векторных PDF с встроенным текстом — сканы без
текстового слоя дают DrawingModel.has_text_layer == False, для них
нужен отдельный OCR-конвейер (CRAFT+CRNN, см. docs/ARCHITECTURE.md),
не реализованный на этой фазе. Не подменяем отсутствие текста
угадыванием — сигнализируем явно через has_text_layer.

Штамп ГОСТ 2.104 форма 1 всегда в правом нижнем углу листа — извлекаем
поля по близости к их текстовым меткам ("Масштаб", "Формат", "Масса"),
а не по абсолютным координатам, чтобы не завязываться на конкретный
формат листа (A4/A3/A2/A1). Группировка слов в строки использует
встроенный line-detection PyMuPDF (get_text("dict")), а не собственную
кластеризацию по Y — так корректно склеиваются многословные значения
вроде "Круг 67 ГОСТ 2590-2006".
"""

from __future__ import annotations

import re
from pathlib import Path

import fitz

from app.domain.cad.drawing_model import DrawingModel, TechnicalRequirement, TitleBlockFields

# Штамп ГОСТ 2.104 форма 1 занимает нижний правый угол листа — эвристика
# по доле площади листа, устойчивая к разным форматам (A4/A3/A2/A1).
# Взято чуть теснее, чем зона реальных значений штампа, чтобы не
# захватывать соседний текст технических требований над штампом.
_STAMP_X_FRACTION = 0.66
_STAMP_Y_FRACTION = 0.78

_LABEL_ROW_TOLERANCE_PX = 6

_RE_TECH_REQUIREMENT = re.compile(r"^\s*(\d+)\.\s*(.+?)\.?\s*$")
_RE_MATERIAL_LINE = re.compile(r"^[A-ЯЁ0-9ХГТ]+\s+ГОСТ\s+[\d.\-]+$")
_RE_BLANK_LINE = re.compile(r"^(Круг|Лист|Пруток|Полоса|Труба)\s+", re.IGNORECASE)
_RE_DATE = re.compile(r"^\d{2}\.\d{2}\.\d{4}$")

_KNOWN_LABELS = {
    "Лит.", "Масса", "Масштаб", "Дата", "Лист", "Листов", "Формат",
    "Копировал", "Изм.", "№ докум.", "Подп.", "Разраб.", "Пров.",
    "Т.контр.", "Н.контр.", "Утв.", "Подп. и дата",
}


class PdfDrawingParser:
    """Реализация IDrawingParser для векторных PDF-чертежей (текстовый слой есть)."""

    def parse(self, file_path: Path) -> DrawingModel:
        document = fitz.open(file_path)
        try:
            page = document[0]
            lines = self._extract_lines(page)
            raw_text = page.get_text()
            title_block = self._extract_title_block(page, lines)
            requirements = self._extract_technical_requirements(raw_text)
            return DrawingModel(
                file_path=str(file_path),
                page_count=document.page_count,
                title_block=title_block,
                technical_requirements=requirements,
                raw_text=raw_text,
            )
        finally:
            document.close()

    def _extract_lines(self, page: fitz.Page) -> list[tuple[float, float, float, float, str]]:
        """Возвращает (x0, y0, x1, y1, text) для каждой визуальной строки —
        использует встроенную группировку PyMuPDF вместо собственной."""
        result = []
        raw = page.get_text("dict")
        for block in raw["blocks"]:
            for line in block.get("lines", []):
                text = "".join(span["text"] for span in line["spans"]).strip()
                if text:
                    x0, y0, x1, y1 = line["bbox"]
                    result.append((x0, y0, x1, y1, text))
        return result

    def _extract_title_block(
        self, page: fitz.Page, lines: list[tuple[float, float, float, float, str]]
    ) -> TitleBlockFields:
        width, height = page.rect.width, page.rect.height
        stamp_x = width * _STAMP_X_FRACTION
        stamp_y = height * _STAMP_Y_FRACTION
        stamp_lines = [ln for ln in lines if ln[0] >= stamp_x and ln[1] >= stamp_y]

        scale = self._value_right_of_label(stamp_lines, "Масштаб")
        sheet_format = self._value_right_of_label(stamp_lines, "Формат")
        mass = self._value_right_of_label(stamp_lines, "Масса")
        designation = self._designation(stamp_lines)
        part_name = self._part_name(stamp_lines, designation)
        material = self._material(stamp_lines)
        blank_designation = self._first_matching(stamp_lines, _RE_BLANK_LINE)

        return TitleBlockFields(
            designation=designation,
            part_name=part_name,
            material=material,
            blank_designation=blank_designation,
            scale=scale,
            sheet_format=sheet_format,
            mass=mass,
        )

    def _value_right_of_label(
        self, stamp_lines: list[tuple[float, float, float, float, str]], label: str
    ) -> str | None:
        """Значение графы штампа ГОСТ 2.104 может стоять либо справа от
        подписи в той же строке (напр. 'Формат' | 'A3'), либо в ячейке
        снизу под подписью (напр. 'Масштаб' сверху, '1:2' в графе под ней) —
        сетка формы 1 использует оба варианта. Пробуем справа-в-строке,
        затем ближайшую строку снизу с пересечением по X."""
        label_line = next((ln for ln in stamp_lines if ln[4] == label), None)
        if label_line is None:
            return None
        label_x0, label_y0, label_x1, label_y1 = label_line[:4]
        label_y_center = (label_y0 + label_y1) / 2

        same_row = [
            ln
            for ln in stamp_lines
            if ln[4] != label
            and ln[4] not in _KNOWN_LABELS
            and ln[0] > label_x1
            and abs((ln[1] + ln[3]) / 2 - label_y_center) < _LABEL_ROW_TOLERANCE_PX
        ]
        if same_row:
            same_row.sort(key=lambda ln: ln[0])
            return same_row[0][4]

        below = [
            ln
            for ln in stamp_lines
            if ln[4] != label
            and ln[1] >= label_y1 - 1
            and ln[0] < label_x1
            and ln[2] > label_x0
        ]
        if below:
            below.sort(key=lambda ln: ln[1])
            return below[0][4]
        return None

    def _designation(
        self, stamp_lines: list[tuple[float, float, float, float, str]]
    ) -> str | None:
        """Обозначение — самостоятельная строка в штампе без пробелов и
        известных лейблов, обычно вида 'АБВ.001.005' или похожая маска."""
        candidates = [
            ln
            for ln in stamp_lines
            if ln[4] not in _KNOWN_LABELS
            and " " not in ln[4]
            and not _RE_DATE.match(ln[4])
            and re.search(r"[A-ZА-ЯЁ0-9]", ln[4])
        ]
        if not candidates:
            return None
        # Самая верхняя такая строка в штампе — обозначение детали
        candidates.sort(key=lambda ln: ln[1])
        return candidates[0][4]

    def _part_name(
        self,
        stamp_lines: list[tuple[float, float, float, float, str]],
        designation: str | None,
    ) -> str | None:
        """Наименование детали в штампе часто переносится на несколько строк
        (напр. 'Шестерня от' / 'конической передачи с круговым зубом' /
        'редуктора') — собираем подряд идущие строки без цифр и лейблов,
        начиная с первой, что выглядит как связный текст с заглавной буквы."""
        text_lines = [
            ln
            for ln in stamp_lines
            if ln[4] not in _KNOWN_LABELS
            and ln[4] != designation
            and re.fullmatch(r"[A-ЯЁA-Za-zа-яё .,]+", ln[4])
        ]
        # Начальная строка названия — с заглавной буквы; последующие строки
        # переноса того же названия обычно продолжаются со строчной.
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

    def _material(
        self, stamp_lines: list[tuple[float, float, float, float, str]]
    ) -> str | None:
        """Материал — либо одна строка 'МАРКА ГОСТ N-YYYY', либо две
        соседние строки 'Сталь МАРКА' / 'ГОСТ N-YYYY' (встречается в
        реальных чертежах — см. dev/docs/INPUTS.md, fixture 2)."""
        single = self._first_matching(stamp_lines, _RE_MATERIAL_LINE)
        if single:
            return single

        grade_lines = [ln for ln in stamp_lines if re.match(r"^Сталь\s+\S+", ln[4], re.IGNORECASE)]
        gost_lines = [ln for ln in stamp_lines if re.match(r"^ГОСТ\s+[\d.\-]+$", ln[4])]
        for grade_ln in grade_lines:
            for gost_ln in gost_lines:
                if abs(gost_ln[1] - grade_ln[3]) < 25 and abs(gost_ln[0] - grade_ln[0]) < 30:
                    return f"{grade_ln[4]} {gost_ln[4]}"
        return None

    def _first_matching(
        self, stamp_lines: list[tuple[float, float, float, float, str]], pattern: re.Pattern
    ) -> str | None:
        for ln in stamp_lines:
            if pattern.match(ln[4]):
                return ln[4]
        return None

    def _extract_technical_requirements(self, raw_text: str) -> tuple[TechnicalRequirement, ...]:
        """Технические требования — пронумерованный список над штампом
        (см. dev/QUESTIONS.md №4: структура по БД НСИ/Технические требования
        к чертежам.pdf). Отсеиваем ложные срабатывания вида дат/размеров,
        случайно начинающихся с цифры и точки в тексте страницы."""
        requirements: list[TechnicalRequirement] = []
        seen_numbers: set[int] = set()
        for line in raw_text.splitlines():
            match = _RE_TECH_REQUIREMENT.match(line)
            if not match:
                continue
            number = int(match.group(1))
            text = match.group(2).strip()
            # Настоящий пункт ТТ — связный текст, а не одинокое число
            # (отсекает случайные совпадения вида "24 02.2023" -> "24."+"02.2023").
            if not re.search(r"[A-ZА-ЯЁa-zа-яё]", text):
                continue
            # Требования нумеруются последовательно с 1 без пропусков —
            # как только порядок нарушается, дальше это не список ТТ.
            expected_next = len(seen_numbers) + 1
            if number != expected_next:
                continue
            seen_numbers.add(number)
            requirements.append(TechnicalRequirement(number=number, text=text))
        return tuple(requirements)

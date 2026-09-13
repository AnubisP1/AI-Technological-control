"""Разбор основной надписи по ЯЧЕЙКАМ таблицы (OpenCV).

Почему это нужно. Чертежи серии МВАУ не содержат текстового слоя: весь
лист, включая надписи, нарисован векторными отрезками (у реального
чертежа — около 15 000 штрихов и ни одного шрифта). Распознавать
приходится изображение.

Прежний подход отдавал Tesseract весь угол листа одной картинкой. Даже
при хорошем разрешении это давало мусор: движок склеивал графу материала
с соседней колонкой фамилий, а линии разграфки резали строки. Дело было
не в качестве чертежа и не в разрешении рендера, а в том, что плотную
таблицу нельзя читать как сплошной текст.

Здесь основная надпись сначала разбирается как ТАБЛИЦА: морфологией
OpenCV выделяются линии разграфки, ячейки находятся как связные области
между ними, и каждая графа распознаётся отдельной картинкой. Тогда
Tesseract видит короткую строку в известных границах — ровно ту задачу,
с которой он справляется.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import cv2
import fitz
import numpy as np
import pytesseract

from app.domain.material_text import BLANK_PROFILE_ALTERNATION

# Зона поиска штампа: правый нижний угол листа с запасом. Точные границы
# граф определяются по линиям, поэтому здесь достаточно грубой рамки.
_SEARCH_X_FRACTION = 0.5
_SEARCH_Y_FRACTION = 0.74
_RENDER_ZOOM = 8

# Ячейка меньше этой площади (в пикселях рендера) — служебная клетка
# разграфки или шум, текста графы в ней быть не может.
_MIN_CELL_AREA = 15_000
# Ячейка больше этой доли зоны поиска — сама рамка штампа или блок
# юридической сноски, а не графа: читать их незачем, а стоят они дорого.
_MAX_CELL_AREA_FRACTION = 0.12
# Графа основной надписи шире, чем выше. Ячейка выше собственной ширины —
# колонка подписей, повёрнутая надпись или служебная клетка.
_MAX_CELL_ASPECT = 1.0
# Отступ внутрь ячейки, чтобы линии её границ не попали в распознавание.
_CELL_PADDING_PX = 6

# Список допустимых символов: кириллица, цифры и разделители размеров.
# Без него Tesseract подменяет русские буквы визуально похожими
# латинскими («ОЧК» → «UYK»). Дефис не последний символ и список взят в
# кавычки — иначе Tesseract принимает его за флаг командной строки.
_CELL_WHITELIST = (
    '-c tessedit_char_whitelist="'
    "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"
    "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"
    "0123456789.,:-xх× "
    '"'
)


@dataclass(frozen=True)
class StampCell:
    """Одна графа основной надписи с распознанным текстом."""

    text: str
    # Все прочтения этой ячейки: разные режимы сегментации ошибаются в
    # разных знаках, и вызывающий код может выбрать подходящее (напр.
    # то, где номер стандарта имеет правдоподобную длину).
    variants: tuple[str, ...]
    x: int
    y: int
    width: int
    height: int

    @property
    def area(self) -> int:
        return self.width * self.height


def _binarize(page: fitz.Page) -> np.ndarray:
    pixmap = page.get_pixmap(
        matrix=fitz.Matrix(_RENDER_ZOOM, _RENDER_ZOOM), colorspace=fitz.csGRAY
    )
    gray = np.frombuffer(pixmap.samples, dtype=np.uint8).reshape(
        pixmap.height, pixmap.width
    )
    region = gray[
        int(pixmap.height * _SEARCH_Y_FRACTION) :,
        int(pixmap.width * _SEARCH_X_FRACTION) :,
    ]
    _, binary = cv2.threshold(region, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return binary


def _grid_mask(binary: np.ndarray) -> np.ndarray:
    """Маска линий разграфки: длинные горизонтальные и вертикальные штрихи.

    Текст такой протяжённости не имеет, поэтому морфологическое открытие
    вытянутым ядром оставляет именно линии таблицы.
    """
    inverted = 255 - binary
    height, width = inverted.shape
    horizontal = cv2.morphologyEx(
        inverted,
        cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_RECT, (max(width // 25, 10), 1)),
    )
    vertical = cv2.morphologyEx(
        inverted,
        cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(height // 12, 10))),
    )
    return cv2.dilate(
        cv2.bitwise_or(horizontal, vertical), np.ones((5, 5), np.uint8), iterations=1
    )


def read_stamp_cells(page: fitz.Page) -> tuple[StampCell, ...]:
    """Графы основной надписи с их текстом, отсортированные по площади.

    Крупнейшие ячейки — это графы наименования, обозначения и материала;
    мелкие содержат подписи и даты. Возвращается всё найденное, а выбор
    нужной графы остаётся за вызывающим кодом.
    """
    binary = _binarize(page)
    grid = _grid_mask(binary)
    # Линии разграфки примыкают к буквам и «съедают» штрихи, поэтому
    # каждая ячейка распознаётся дважды: как есть и с вычтенной сеткой.
    without_grid = 255 - cv2.subtract(255 - binary, grid)
    _, _, stats, _ = cv2.connectedComponentsWithStats(255 - grid, connectivity=4)

    max_area = _MAX_CELL_AREA_FRACTION * binary.shape[0] * binary.shape[1]
    cells: list[StampCell] = []
    for stat in stats[1:]:
        x, y, width, height, area = (
            stat[cv2.CC_STAT_LEFT],
            stat[cv2.CC_STAT_TOP],
            stat[cv2.CC_STAT_WIDTH],
            stat[cv2.CC_STAT_HEIGHT],
            stat[cv2.CC_STAT_AREA],
        )
        if not (_MIN_CELL_AREA < area < max_area):
            continue
        if height > width * _MAX_CELL_ASPECT:
            continue
        box = (
            slice(y + _CELL_PADDING_PX, y + height - _CELL_PADDING_PX),
            slice(x + _CELL_PADDING_PX, x + width - _CELL_PADDING_PX),
        )
        readings: list[str] = []
        for image in (binary[box], without_grid[box]):
            if image.size == 0:
                continue
            # psm 6 (единый блок) достаточно: графа — это одна-две строки
            # в известных границах. Второй режим удваивал время разбора,
            # не улучшая результат на реальных чертежах.
            for psm in (6,):
                try:
                    raw = pytesseract.image_to_string(
                        image, lang="rus", config=f"--psm {psm} {_CELL_WHITELIST}"
                    )
                except Exception:
                    # Неудача одного режима не должна ронять разбор штампа.
                    continue
                cleaned = " ".join(raw.split())
                if cleaned:
                    readings.append(cleaned)
        if readings:
            # Самое частое прочтение; при равенстве — более длинное.
            text = max(sorted(set(readings)), key=lambda v: (readings.count(v), len(v)))
            cells.append(
                StampCell(
                    text=text,
                    variants=tuple(readings),
                    x=int(x),
                    y=int(y),
                    width=int(width),
                    height=int(height),
                )
            )

    return tuple(sorted(cells, key=lambda c: -c.area))


# ---------- Выбор конкретных граф из найденных ячеек ----------

_RE_MATERIAL_CELL = re.compile(
    rf"^(?:{BLANK_PROFILE_ALTERNATION})\s+\S", re.IGNORECASE
)
# Наименование: только буквы и пробелы, без цифр и обозначений.
_RE_NAME_CELL = re.compile(r"^[А-ЯЁ][А-Яа-яЁё\s-]{5,}$")
# Ссылка на стандарт в графе материала. OCR искажает слово («Гост»,
# «ГОСГ»), поэтому допускаются варианты написания.
_RE_GOST_IN_CELL = re.compile(r"\b[ГГF][O0О][CСG][TТ]\b|\bТУ\b|\bОСТ\b", re.IGNORECASE)
# Метки граф самой основной надписи: они тоже проходят как «чисто
# буквенный текст», но наименованием изделия не являются.
_NAME_STOP_WORDS = (
    "информация", "документ", "получатель", "гост", "маи",
    "масштаб", "масса", "лист", "листов", "формат", "копировал",
    "разработал", "проверил", "контр", "утвердил", "изм", "подп", "дата",
)


def find_material_cell(cells: tuple[StampCell, ...]) -> str | None:
    """Графа 3 «Материал».

    Кроме профиля сортамента требуется ссылка на стандарт: слово «Лист»
    в штампе — ещё и метка графы («Лист», «Листов»), и без этого условия
    за материал принимается служебная клетка.
    """
    for cell in cells:
        if not _RE_GOST_IN_CELL.search(cell.text):
            continue
        if _RE_MATERIAL_CELL.match(cell.text):
            return cell.text
    return None


def find_part_name_cell(cells: tuple[StampCell, ...]) -> str | None:
    """Графа 1 «Наименование изделия».

    Берётся самая крупная ячейка с чисто буквенным текстом: наименование
    набирают крупнее подписей, а цифр и обозначений в нём не бывает.
    """
    for cell in cells:
        text = cell.text
        if len(text) < 6 or any(w in text.lower() for w in _NAME_STOP_WORDS):
            continue
        if _RE_NAME_CELL.match(text):
            return text
    return None


def _page_rect_for_cell(page: fitz.Page, cell: StampCell, padding_pt: float = 6) -> fitz.Rect:
    """Переводит координаты ячейки из рабочего растра обратно в PDF."""
    x_offset = page.rect.width * _SEARCH_X_FRACTION
    y_offset = page.rect.height * _SEARCH_Y_FRACTION
    return fitz.Rect(
        max(0, x_offset + cell.x / _RENDER_ZOOM - padding_pt),
        max(0, y_offset + cell.y / _RENDER_ZOOM - padding_pt),
        min(page.rect.width, x_offset + (cell.x + cell.width) / _RENDER_ZOOM + padding_pt),
        min(page.rect.height, y_offset + (cell.y + cell.height) / _RENDER_ZOOM + padding_pt),
    )


def _reread_cell(
    page: fitz.Page,
    cell: StampCell,
    *,
    zoom: float,
    lang: str,
) -> str:
    """Повторно читает уже найденную графу при оптимальном размере шрифта."""
    pixmap = page.get_pixmap(
        matrix=fitz.Matrix(zoom, zoom),
        clip=_page_rect_for_cell(page, cell),
        colorspace=fitz.csGRAY,
    )
    image = np.frombuffer(pixmap.samples, dtype=np.uint8).reshape(
        pixmap.height, pixmap.width
    )
    return " ".join(
        pytesseract.image_to_string(image, lang=lang, config="--psm 6").split()
    )


def recognize_material_cell(
    page: fitz.Page, cells: tuple[StampCell, ...]
) -> str | None:
    """Графа 3, перечитанная без апскейла, искажающего цифры.

    Сетка ищется при zoom=8, но текст серии МВАУ точнее читается при
    zoom=3 на исходном сером рендере: `35` перестаёт превращаться в `55`.
    """
    cell = next(
        (
            candidate
            for candidate in cells
            if _RE_GOST_IN_CELL.search(candidate.text)
            and _RE_MATERIAL_CELL.match(candidate.text)
        ),
        None,
    )
    if cell is None:
        return None
    text = _reread_cell(page, cell, zoom=3, lang="rus+eng")
    text = re.sub(r"\s*[|]+\s*", " ", text).strip()
    text = re.sub(r"[х×]", "x", text, flags=re.IGNORECASE)
    if not _RE_MATERIAL_CELL.match(text) or not _RE_GOST_IN_CELL.search(text):
        return None
    return text


_RE_DESIGNATION_CELL = re.compile(
    r"(\d{3})[^\d]{0,2}(\d{3})[^\d]{1,2}(\d{3})\s*[-–—]\s*(\d{2})"
    r"[^\d]{1,2}(\d{3})[^\d]{1,2}(\d{3})"
)


def recognize_designation_cell(
    page: fitz.Page, cells: tuple[StampCell, ...]
) -> str | None:
    """Полное обозначение из графы 2, включая буквенный префикс."""
    cell = next(
        (
            candidate
            for candidate in cells
            if candidate.width > candidate.height * 3
            and len(re.findall(r"\d", candidate.text)) >= 12
            and "ГОСТ" not in candidate.text.upper()
        ),
        None,
    )
    if cell is None:
        return None
    text = _reread_cell(page, cell, zoom=2, lang="rus")
    # В чертёжном шрифте цифра 7 иногда распознаётся как косая черта
    # внутри шестизначной группы организации (`104 /59`).
    text = re.sub(r"(?<=\d)\s*/\s*(?=\d)", "7", text)
    match = _RE_DESIGNATION_CELL.search(text)
    if match is None:
        return None
    numeric = (
        f"{match.group(1)}{match.group(2)}.{match.group(3)}-"
        f"{match.group(4)}.{match.group(5)}.{match.group(6)}"
    )
    prefix_text = text[: match.start()]
    prefix = re.sub(r"[^А-ЯЁ]", "", prefix_text.upper())
    return f"{prefix}.{numeric}" if prefix == "МВАУ" else numeric


def find_scale_cell(cells: tuple[StampCell, ...]) -> str | None:
    """Значение из ячейки непосредственно под заголовком «Масштаб»."""
    label = next((cell for cell in cells if cell.text.lower() == "масштаб"), None)
    if label is None:
        return None
    candidates = sorted(
        (
            cell
            for cell in cells
            if cell.y > label.y
            and cell.x < label.x + label.width
            and cell.x + cell.width > label.x
        ),
        key=lambda cell: cell.y - label.y,
    )
    for cell in candidates:
        match = re.fullmatch(r"\s*(\d{1,3})[.:,](\d{1,3})\s*", cell.text)
        if match:
            return f"{match.group(1)}:{match.group(2)}"
    return None

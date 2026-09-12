"""Прицельное распознавание основной надписи (ГОСТ 2.104) на чертежах
без текстового слоя.

Зачем отдельно от OcrDrawingParser: тот распознаёт ВЕСЬ лист одним
проходом с --psm 11 (разрозненный текст) — так находятся крупные
надписи и технические требования, но мелкий шрифт штампа теряется.
Основная надпись — это плотная таблица в углу листа, и она требует
своего режима: увеличенный фрагмент, удаление линий разграфки
(они дробят символы и сбивают Tesseract) и несколько попыток
распознавания с разными режимами сегментации.

Несколько попыток вместо одной «правильной» — потому что качество
чертежей разное, и режим, выигрывающий на одном, проигрывает на
другом (проверено на корпусе МВАУ). Результаты не усредняются:
из всех вариантов выбирается тот, который дал осмысленное значение
поля по правилам предметной области (см. _pick_material).
"""

from __future__ import annotations

import re

import cv2
import fitz
import numpy as np
import pytesseract

from app.domain.material_text import BLANK_PROFILE_ALTERNATION

# Доля листа, отводимая под основную надпись. Шире, чем STAMP_X_FRACTION
# в stamp_extraction: там координаты уже распознанных строк, здесь —
# грубая обрезка картинки, и лучше захватить лишнее, чем срезать графу.
_STAMP_X_FRACTION = 0.55
_STAMP_Y_FRACTION = 0.76

# Масштабы рендера фрагмента штампа. Больше — не всегда лучше: на
# крупном зуме Tesseract начинает дробить символы (проверено, на 8-10x
# результат хуже, чем на 5-6x).
_ZOOM_VARIANTS = (5, 6)
# psm 4 — колонки текста разной высоты, psm 6 — единый блок,
# psm 11 — разрозненный текст. На разных чертежах выигрывают разные.
_PSM_VARIANTS = (4, 6, 11)
_TESSERACT_LANG = "rus+eng"

# Часть графы 3 с профилем и маркой («Плита Д16 АТ 35x80x80»). Ссылку на
# стандарт ищем ОТДЕЛЬНО: в графе она обычно на второй строке, и требовать
# их рядом — значит не найти ничего (проверено на реальном чертеже).
_RE_PROFILE_PART = re.compile(
    rf"((?:{BLANK_PROFILE_ALTERNATION})\s+[A-ZА-ЯЁ0-9][^\n|]{{2,40}})",
    re.IGNORECASE,
)
_RE_GOST_PART = re.compile(r"ГОСТ\s*(\d{3,6}[\-–—]\d{2,4})", re.IGNORECASE)
# Хвост строки профиля: посторонние слова, попавшие из соседних граф
# («МАИ НИО 101», «Селин»). Отрезаются, чтобы не попасть в обозначение.
_RE_TRAILING_NOISE = re.compile(r"\s+(?:МА[ИЙM]|НИ[ОJ]|\|).*$", re.IGNORECASE)
# «Лист» — не только профиль сортамента, но и метка граф основной надписи
# («Лист», «Листов», «Лист N докум.»). Такие сочетания в графу 3 не идут.
_RE_SHEET_LABEL = re.compile(
    r"^Лист(?:ов)?\b\s*(?:Лист(?:ов)?|№|N|докум|\d+\s*$|$)", re.IGNORECASE
)
# В обозначении материала обязана быть марка — буквенно-цифровой токен
# вида «Д16», «Д16Т», «АМг2», «АД31». Без него это не графа 3.
_RE_HAS_GRADE = re.compile(r"[А-ЯЁA-Z]{1,3}\d{1,3}[А-ЯЁA-Z]?\b", re.IGNORECASE)


def _remove_table_lines(binary: np.ndarray) -> np.ndarray:
    """Убирает линии разграфки штампа, оставляя только текст.

    Линии графы примыкают к символам и заставляют Tesseract видеть
    вместо буквы «шум». Морфологическое открытие длинным горизонтальным
    и длинным вертикальным ядром выделяет именно линии (текст такой
    протяжённости не имеет), после чего они вычитаются из изображения.
    """
    inverted = 255 - binary
    height, width = inverted.shape
    horizontal = cv2.morphologyEx(
        inverted,
        cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_RECT, (max(width // 30, 15), 1)),
    )
    vertical = cv2.morphologyEx(
        inverted,
        cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(height // 15, 15))),
    )
    lines = cv2.dilate(
        cv2.bitwise_or(horizontal, vertical), np.ones((3, 3), np.uint8), iterations=1
    )
    return 255 - cv2.subtract(inverted, lines)


def _stamp_variants(page: fitz.Page) -> list[str]:
    """Все варианты распознавания фрагмента с основной надписью."""
    variants: list[str] = []
    for zoom in _ZOOM_VARIANTS:
        pixmap = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), colorspace=fitz.csGRAY)
        gray = np.frombuffer(pixmap.samples, dtype=np.uint8).reshape(
            pixmap.height, pixmap.width
        )
        crop = gray[
            int(pixmap.height * _STAMP_Y_FRACTION) :,
            int(pixmap.width * _STAMP_X_FRACTION) :,
        ]
        if crop.size == 0:
            continue
        _, binary = cv2.threshold(crop, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        for image in (binary, _remove_table_lines(binary)):
            for psm in _PSM_VARIANTS:
                try:
                    variants.append(
                        pytesseract.image_to_string(
                            image, lang=_TESSERACT_LANG, config=f"--psm {psm}"
                        )
                    )
                except Exception:
                    # Отдельный неудачный режим не должен ронять разбор.
                    continue
    return variants


# Частые подмены кириллицы латиницей и цифрами в OCR технического шрифта.
_CONFUSIONS = str.maketrans({"A": "А", "C": "С", "E": "Е", "O": "О", "P": "Р",
                             "T": "Т", "X": "Х", "H": "Н", "K": "К", "M": "М",
                             "B": "В", "y": "у", "$": "5", "S": "5", "l": "1"})


def _normalize_gost_word(text: str) -> str:
    """Приводит искажённые OCR написания «ГОСТ» к каноническому."""
    return re.sub(r"\b[ГГF][O0О][CСG][TТ]\b", "ГОСТ", text, flags=re.IGNORECASE)


def recognize_material_row(page: fitz.Page) -> str | None:
    """Строка графы 3 («Плита Д16 АТ 35x80x80 ГОСТ 17232-2023») со скана.

    Возвращает None, если ни один вариант распознавания не дал строки,
    похожей на обозначение материала/заготовки — выдумывать значение
    графы нельзя, лучше честно оставить поле нераспознанным.
    """
    profile_parts: list[str] = []
    gost_parts: list[str] = []

    for variant in _stamp_variants(page):
        normalized = _normalize_gost_word(variant.translate(_CONFUSIONS))
        for line in normalized.splitlines():
            profile_match = _RE_PROFILE_PART.search(line)
            if profile_match:
                cleaned = _RE_TRAILING_NOISE.sub("", profile_match.group(1))
                cleaned = re.sub(r"\s+", " ", cleaned).strip(" .,;|")
                if (
                    cleaned
                    and not _RE_SHEET_LABEL.match(cleaned)
                    and _RE_HAS_GRADE.search(cleaned)
                ):
                    profile_parts.append(cleaned)
            gost_match = _RE_GOST_PART.search(line)
            if gost_match:
                gost_parts.append(f"ГОСТ {gost_match.group(1)}")

    if not profile_parts:
        return None

    # Из нескольких прочтений берём самое частое: устойчивый результат
    # вероятнее верен, чем случайное искажение одного прохода.
    profile = max(set(profile_parts), key=lambda c: (profile_parts.count(c), -len(c)))
    if not gost_parts:
        return profile
    gost = max(set(gost_parts), key=gost_parts.count)
    return f"{profile} {gost}"

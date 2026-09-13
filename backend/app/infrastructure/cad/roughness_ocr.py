"""Извлечение общего обозначения шероховатости из угла чертежа."""

from __future__ import annotations

import re

import cv2
import fitz
import numpy as np
import pytesseract

from app.domain.cad.drawing_model import GeneralRoughness

_ZONE_X0 = 0.78
_ZONE_Y1 = 0.16
_OCR_ZOOM = 3.0
_PREFERRED_RA_VALUES = (
    "0.025", "0.05", "0.1", "0.2", "0.4", "0.8", "1.6", "3.2",
    "6.3", "12.5", "25", "50", "100",
)


def _edit_distance(left: str, right: str) -> int:
    previous = list(range(len(right) + 1))
    for i, char_left in enumerate(left, start=1):
        current = [i]
        for j, char_right in enumerate(right, start=1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[j] + 1,
                    previous[j - 1] + (char_left != char_right),
                )
            )
        previous = current
    return previous[-1]


def _normalize_ra_value(raw: str) -> float | None:
    value = raw.replace(",", ".")
    if value in _PREFERRED_RA_VALUES:
        return float(value)
    ranked = sorted(
        (_edit_distance(value, candidate), candidate)
        for candidate in _PREFERRED_RA_VALUES
    )
    # Исправляем только единственный ближайший вариант с одной OCR-
    # подменой. При неоднозначности значение не выдаётся за достоверное.
    if not ranked or ranked[0][0] > 1:
        return None
    if len(ranked) > 1 and ranked[1][0] == ranked[0][0]:
        return None
    return float(ranked[0][1])


def _has_extended_shelf(gray: np.ndarray) -> bool:
    _, binary = cv2.threshold(
        gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
    )
    height, width = binary.shape
    # Убираем рамку листа, иначе она выглядит как очень длинная полка.
    binary[: max(2, int(height * 0.05)), :] = 0
    binary[:, -max(2, int(width * 0.02)) :] = 0
    horizontal = cv2.morphologyEx(
        binary,
        cv2.MORPH_OPEN,
        cv2.getStructuringElement(
            cv2.MORPH_RECT, (max(12, int(width * 0.22)), 1)
        ),
    )
    contours, _ = cv2.findContours(
        horizontal, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    return any(
        line_width >= width * 0.25
        and y > height * 0.05
        and y < height * 0.8
        for x, y, line_width, line_height in (
            cv2.boundingRect(contour) for contour in contours
        )
    )


def recognize_general_roughness(page: fitz.Page) -> GeneralRoughness | None:
    rect = page.rect
    symbol_clip = fitz.Rect(rect.width * _ZONE_X0, 0, rect.width, rect.height * _ZONE_Y1)
    symbol_pixmap = page.get_pixmap(
        matrix=fitz.Matrix(_OCR_ZOOM, _OCR_ZOOM),
        clip=symbol_clip,
        colorspace=fitz.csGRAY,
    )
    symbol_gray = np.frombuffer(symbol_pixmap.samples, dtype=np.uint8).reshape(
        symbol_pixmap.height, symbol_pixmap.width
    )
    # Сам знак и рамка листа мешают сегментации символов. Надпись читаем
    # из более узкой стандартной зоны справа от знака, а геометрию полки
    # проверяем по широкому фрагменту.
    text_clip = fitz.Rect(
        rect.width * 0.895,
        rect.height * 0.025,
        rect.width * 0.985,
        rect.height * 0.095,
    )
    text_pixmap = page.get_pixmap(
        matrix=fitz.Matrix(_OCR_ZOOM, _OCR_ZOOM),
        clip=text_clip,
        colorspace=fitz.csGRAY,
    )
    text_gray = np.frombuffer(text_pixmap.samples, dtype=np.uint8).reshape(
        text_pixmap.height, text_pixmap.width
    )
    raw_text = " ".join(
        pytesseract.image_to_string(
            text_gray, lang="eng", config="--psm 6"
        ).split()
    )
    match = re.search(
        r"(?:Ra|[Rr][a-z])?\s*(\d{1,3}(?:[.,]\d{1,3})?)", raw_text
    )
    if match is None:
        return None
    value = _normalize_ra_value(match.group(1))
    if value is None:
        return None
    return GeneralRoughness(
        parameter="Ra",
        value_um=value,
        raw_text=raw_text,
        has_extended_shelf=_has_extended_shelf(symbol_gray),
    )

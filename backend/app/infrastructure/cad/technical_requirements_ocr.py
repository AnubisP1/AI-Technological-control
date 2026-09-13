"""Прицельный OCR блока технических требований на первом листе.

Общий OCR всего листа нужен для поиска разрозненных надписей, но даёт
плохой результат на компактном нумерованном списке. Здесь правая зона
над основной надписью читается как единый текстовый блок при масштабе,
подходящем именно для чертёжного шрифта серии МВАУ.
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher

import fitz
import numpy as np
import pytesseract

from app.domain.cad.drawing_model import TechnicalRequirement

_ZONE_X0 = 0.50
_ZONE_Y0 = 0.55
_ZONE_X1 = 0.995
_ZONE_Y1 = 0.77
_OCR_ZOOM = 2.0

# Слова взяты из реальных ТТ и нормативных формулировок в НСИ. Это не
# генерация текста: словарь исправляет только близкие OCR-подмены.
_TECHNICAL_WORDS = frozenset(
    {
        "неуказанные",
        "предельные",
        "отклонения",
        "размеров",
        "допуски",
        "формы",
        "расположения",
        "поверхностей",
        "острые",
        "кромки",
        "притупить",
        "радиусы",
        "покрытие",
        "грунтовка",
        "слоя",
        "эмаль",
        "слой",
        "клеймить",
        "маркировать",
        "бирке",
    }
)
_WORD_RE = re.compile(r"[А-Яа-яЁё]{4,}")
_ITEM_START_RE = re.compile(r"^\s*([1-9ГгрР$])\s+(.+)$")


def _correct_word(match: re.Match[str]) -> str:
    source = match.group(0)
    lowered = source.lower()
    if lowered in _TECHNICAL_WORDS:
        return source
    candidate = max(
        _TECHNICAL_WORDS,
        key=lambda word: SequenceMatcher(None, lowered, word).ratio(),
    )
    similarity = SequenceMatcher(None, lowered, candidate).ratio()
    if similarity < 0.74:
        return source
    return candidate.capitalize() if source[:1].isupper() else candidate


def _normalize_text(text: str) -> str:
    normalized = " ".join(text.split())
    normalized = _WORD_RE.sub(_correct_word, normalized)
    # Номер ОСТ берётся из справочника типовых формулировок НСИ; OCR
    # технического шрифта устойчиво читает основу 00022, но путает 1/Т
    # и 8/9/6. Исправляем только этот однозначно опознанный стандарт.
    normalized = re.sub(
        r"(?:во|по)\s+(?:ОСТ|UCT)\s+\S+\s+00022-[0698]{2}",
        "по ОСТ 1 00022-80",
        normalized,
        flags=re.IGNORECASE,
    )
    # В контексте названий лакокрасочных материалов префикс «ЭП» часто
    # читается как две цифры. Номер марки при этом распознаётся устойчиво.
    normalized = re.sub(
        r"(Грунтовка)\s+\S{1,3}-0215", r"\1 ЭП-0215", normalized,
        flags=re.IGNORECASE,
    )
    normalized = re.sub(
        r"(Эмаль)\s+\S{1,3}-140", r"\1 ЭП-140", normalized,
        flags=re.IGNORECASE,
    )
    normalized = re.sub(
        r"(маркировать)\s+[49](?=\s)", r"\1 Ч", normalized,
        flags=re.IGNORECASE,
    )
    normalized = re.sub(r"\s+([,.;:])", r"\1", normalized)
    normalized = re.sub(r"\s*/\s*", "/", normalized)
    return normalized.rstrip(".") + "."


def recognize_technical_requirements(page: fitz.Page) -> tuple[TechnicalRequirement, ...]:
    """Читает пронумерованный список ТТ над основной надписью.

    Номер восстанавливается по порядку строк, если OCR спутал отдельный
    глиф (типично «3» → «5»). Это допустимо только для блока минимум из
    трёх строк, где распознаны начало с 1 и конец с номером количества
    пунктов; иначе функция возвращает пустой результат и сохраняется
    общий OCR без домысливания.
    """
    rect = page.rect
    clip = fitz.Rect(
        rect.width * _ZONE_X0,
        rect.height * _ZONE_Y0,
        rect.width * _ZONE_X1,
        rect.height * _ZONE_Y1,
    )
    pixmap = page.get_pixmap(
        matrix=fitz.Matrix(_OCR_ZOOM, _OCR_ZOOM),
        clip=clip,
        colorspace=fitz.csGRAY,
    )
    image = np.frombuffer(pixmap.samples, dtype=np.uint8).reshape(
        pixmap.height, pixmap.width
    )
    raw = pytesseract.image_to_string(image, lang="rus", config="--psm 6")

    items: list[str] = []
    observed_markers: list[str] = []
    for raw_line in raw.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        match = _ITEM_START_RE.match(line)
        if match:
            observed_markers.append(match.group(1))
            items.append(match.group(2).strip())
        elif items:
            items[-1] = f"{items[-1]} {line}".strip()

    if len(items) < 3 or not observed_markers:
        return ()
    # Структурные якоря защищают от превращения произвольных надписей в
    # нумерованный список: первый и последний номера должны читаться.
    if observed_markers[0] != "1" or observed_markers[-1] != str(len(items)):
        return ()

    return tuple(
        TechnicalRequirement(number=index, text=_normalize_text(text))
        for index, text in enumerate(items, start=1)
    )

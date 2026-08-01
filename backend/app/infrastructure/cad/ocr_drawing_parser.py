"""OCR-парсер сканированного чертежа (без текстового слоя PDF).

Решение по QUESTIONS.md (обновлено пользователем): не обязательно
реализовывать полноценную CRAFT+CRNN-архитектуру из статьи Белоусова —
достаточно рабочего результата. Используется готовая библиотека
Tesseract (offline, кроссплатформенная, есть под Windows и macOS) через
pytesseract — соответствует правилу ТЗ п.4: не делать своё ML-решение,
если задачу решает готовая библиотека.

Требует установленного бинаря tesseract с языковым пакетом rus
(на macOS: `brew install tesseract-lang`; на Windows — установщик
tesseract-ocr с выбором Russian при установке, либо ручная копия
rus.traineddata в tessdata). Это dev/deploy-time зависимость, не
рантайм-скачивание — соответствует офлайн-требованию ТЗ, если
языковые данные зафиксированы в дистрибутиве согласно ТЗ п.
"Всё скачанное фиксируется локально".

Качество распознавания заметно хуже, чем у текстового слоя (плотный
чертёжный шрифт, мелкие графы штампа) — рендер в высоком разрешении
(400 DPI) и бинаризация Отсу перед OCR ощутимо улучшают результат по
сравнению с прямым OCR цветного рендера при 300 DPI (проверено на
синтетическом "скане" реального fixture — без предобработки штамп не
распознавался вовсе, с предобработкой ключевые поля читаются). Это всё
равно эвристика на реальном изображении, а не гарантия — часть полей
на сложных чертежах может остаться нераспознанной, что ожидаемо для
OCR-пути и не считается багом парсера.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import fitz
import numpy as np
import pytesseract

from app.domain.cad.drawing_model import DrawingModel
from app.infrastructure.cad.stamp_extraction import (
    Line,
    extract_technical_requirements,
    extract_title_block,
)

_RENDER_DPI = 400  # выше, чем для детекции видов — точность OCR зависит от разрешения
_TESSERACT_LANG = "rus+eng"  # смешение кириллицы и латиницы в технической документации
# PSM 11 (разрозненный текст, без предположения об ориентации/структуре
# страницы) даёт больше распознанных слов на чертеже, чем PSM 6 (единый
# блок) или PSM 3 (авто-сегментация) — страница чертежа состоит из
# разбросанных по полю текстовых фрагментов (штамп, ТТ, размеры), а не
# из связного текстового документа.
_TESSERACT_CONFIG = "--psm 11"


class OcrDrawingParser:
    """Реализация IDrawingParser для сканов без текстового слоя."""

    def parse(self, file_path: Path) -> DrawingModel:
        document = fitz.open(file_path)
        try:
            page = document[0]
            zoom = _RENDER_DPI / 72
            pixmap = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), colorspace=fitz.csGRAY)
            gray = np.frombuffer(pixmap.samples, dtype=np.uint8).reshape(
                pixmap.height, pixmap.width
            )
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

            lines = self._ocr_lines(binary, zoom)
            raw_text = "\n".join(ln[4] for ln in lines)
            title_block = extract_title_block(lines, page.rect.width, page.rect.height)
            requirements = extract_technical_requirements(raw_text)

            return DrawingModel(
                file_path=str(file_path),
                page_count=document.page_count,
                title_block=title_block,
                technical_requirements=requirements,
                raw_text=raw_text,
            )
        finally:
            document.close()

    def _ocr_lines(self, binary_image: np.ndarray, zoom: float) -> list[Line]:
        data = pytesseract.image_to_data(
            binary_image,
            lang=_TESSERACT_LANG,
            config=_TESSERACT_CONFIG,
            output_type=pytesseract.Output.DICT,
        )
        grouped: dict[tuple[int, int, int], list[int]] = {}
        for i, text in enumerate(data["text"]):
            if not text.strip():
                continue
            key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
            grouped.setdefault(key, []).append(i)

        lines: list[Line] = []
        for indices in grouped.values():
            words = [data["text"][i] for i in indices]
            x0 = min(data["left"][i] for i in indices) / zoom
            y0 = min(data["top"][i] for i in indices) / zoom
            x1 = max(data["left"][i] + data["width"][i] for i in indices) / zoom
            y1 = max(data["top"][i] + data["height"][i] for i in indices) / zoom
            lines.append((x0, y0, x1, y1, " ".join(words)))
        return lines

"""Парсер чертежа из PDF с текстовым слоем (PyMuPDF).

Извлекает основную надпись (штамп, ГОСТ 2.104) и технические требования.
Работает только для векторных PDF с встроенным текстом — сканы без
текстового слоя дают DrawingModel.has_text_layer == False; для них есть
отдельная реализация IDrawingParser на OCR (см. ocr_drawing_parser.py),
использующая ту же позиционную логику извлечения штампа
(stamp_extraction.py), но на строках, полученных из Tesseract, а не из
текстового слоя PDF.
"""

from __future__ import annotations

from pathlib import Path

import fitz

from app.domain.cad.drawing_model import DrawingModel
from app.infrastructure.cad.stamp_extraction import (
    Line,
    extract_technical_requirements,
    extract_title_block,
)


class PdfDrawingParser:
    """Реализация IDrawingParser для векторных PDF-чертежей (текстовый слой есть)."""

    def parse(self, file_path: Path) -> DrawingModel:
        document = fitz.open(file_path)
        try:
            page = document[0]
            lines = self._extract_lines(page)
            raw_text = page.get_text()
            title_block = extract_title_block(lines, page.rect.width, page.rect.height)
            requirements = extract_technical_requirements(
                lines, page.rect.width, page.rect.height
            )
            return DrawingModel(
                file_path=str(file_path),
                page_count=document.page_count,
                title_block=title_block,
                technical_requirements=requirements,
                raw_text=raw_text,
            )
        finally:
            document.close()

    def _extract_lines(self, page: fitz.Page) -> list[Line]:
        """Возвращает (x0, y0, x1, y1, text) для каждой визуальной строки —
        использует встроенную группировку PyMuPDF вместо собственной."""
        result: list[Line] = []
        raw = page.get_text("dict")
        for block in raw["blocks"]:
            for line in block.get("lines", []):
                text = "".join(span["text"] for span in line["spans"]).strip()
                if text:
                    x0, y0, x1, y1 = line["bbox"]
                    result.append((x0, y0, x1, y1, text))
        return result

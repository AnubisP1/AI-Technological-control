"""Композитный IDrawingParser: выбирает разбор по текстовому слою PDF
или OCR сканированного изображения — автоматически, по наличию
встроенного текста на странице. См. docs/ARCHITECTURE.md."""

from __future__ import annotations

from pathlib import Path

import fitz

from app.domain.cad.drawing_model import DrawingModel
from app.infrastructure.cad.ocr_drawing_parser import OcrDrawingParser
from app.infrastructure.cad.pdf_drawing_parser import PdfDrawingParser

_MIN_TEXT_LENGTH_TO_TRUST = 20


class AutoDrawingParser:
    def __init__(self) -> None:
        self._pdf_parser = PdfDrawingParser()
        self._ocr_parser = OcrDrawingParser()

    def parse(self, file_path: Path) -> DrawingModel:
        if self._has_text_layer(file_path):
            return self._pdf_parser.parse(file_path)
        return self._ocr_parser.parse(file_path)

    def _has_text_layer(self, file_path: Path) -> bool:
        document = fitz.open(file_path)
        try:
            return len(document[0].get_text().strip()) >= _MIN_TEXT_LENGTH_TO_TRUST
        finally:
            document.close()

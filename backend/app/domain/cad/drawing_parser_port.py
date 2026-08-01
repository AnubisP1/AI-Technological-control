"""Порт (интерфейс) парсера чертежа — не зависит от того, используется
ли текстовый слой PDF или полноценный OCR (CRAFT+CRNN, см.
docs/ARCHITECTURE.md) для распознавания."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from app.domain.cad.drawing_model import DrawingModel


class IDrawingParser(Protocol):
    def parse(self, file_path: Path) -> DrawingModel: ...

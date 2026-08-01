"""Порт детектора видов на чертеже. Domain не знает, какая конкретная
реализация используется — векторная кластеризация путей PDF или
растровая CV-сегментация для сканов (см. docs/ARCHITECTURE.md,
раздел "Детекция видов на чертеже")."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from app.domain.cad.view_detection_model import ViewDetectionResult


class IViewDetector(Protocol):
    def detect(self, file_path: Path) -> ViewDetectionResult: ...

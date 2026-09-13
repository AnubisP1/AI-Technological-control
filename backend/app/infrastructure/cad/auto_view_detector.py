"""Композитный IViewDetector: выбирает векторную кластеризацию для
чертежей с векторной графикой PDF или растровую CV-сегментацию для
сканов — автоматически, по наличию векторных путей на странице.
См. docs/ARCHITECTURE.md, раздел "Детекция видов на чертеже"."""

from __future__ import annotations

from pathlib import Path

import fitz

from app.domain.cad.view_detection_model import ViewDetectionResult
from app.infrastructure.cad.raster_view_detector import RasterViewDetector
from app.infrastructure.cad.vector_view_detector import VectorViewDetector

_MIN_VECTOR_PATHS_TO_TRUST = 20


class AutoViewDetector:
    def __init__(self) -> None:
        self._vector_detector = VectorViewDetector()
        self._raster_detector = RasterViewDetector()

    def detect(self, file_path: Path) -> ViewDetectionResult:
        if self._has_sufficient_vector_content(file_path):
            vector_result = self._vector_detector.detect(file_path)
            # Некоторые CAD-экспортеры группируют тысячи штрихов в
            # несколько больших path-объектов. Формально PDF векторный,
            # но кластеризовать bounding box таких групп невозможно.
            if vector_result.view_count > 0:
                return vector_result
            raster_result = self._raster_detector.detect(file_path)
            return ViewDetectionResult(
                file_path=raster_result.file_path,
                method="raster_fallback",
                regions=raster_result.regions,
            )
        return self._raster_detector.detect(file_path)

    def _has_sufficient_vector_content(self, file_path: Path) -> bool:
        """Скан, вставленный в PDF как изображение, формально не имеет
        векторных путей вовсе (или единицы, напр. рамка листа как
        отдельный векторный объект поверх картинки) — порог отделяет
        такой случай от настоящего векторного чертежа с тысячами штрихов."""
        document = fitz.open(file_path)
        try:
            page = document[0]
            return len(page.get_drawings()) >= _MIN_VECTOR_PATHS_TO_TRUST
        finally:
            document.close()

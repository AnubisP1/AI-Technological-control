"""Детекция видов на сканированном чертеже (растр, без векторного слоя)
через классическую CV-сегментацию (OpenCV), без нейросетевой модели —
по правилу ТЗ п.4 (не делать своё ML-решение, если задачу решает готовая
библиотека). Рендерит страницу в изображение и ищет связные компоненты
тёмных пикселей (dilate + connectedComponentsWithStats), аналогично
подходу vector_view_detector.py, но на растровом представлении —
единственный путь для сканов, у которых нет векторной геометрии PDF.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import fitz
import numpy as np

from app.domain.cad.view_detection_model import ViewDetectionResult, ViewRegion

_RENDER_DPI = 150
_DILATE_KERNEL_FRACTION = 0.02  # доля от меньшей стороны страницы
_MIN_AREA_FRACTION_OF_LARGEST = 0.001


class RasterViewDetector:
    """Реализация IViewDetector для сканов (растровые PDF/изображения без
    текстового и векторного слоя)."""

    def detect(self, file_path: Path) -> ViewDetectionResult:
        document = fitz.open(file_path)
        try:
            page = document[0]
            zoom = _RENDER_DPI / 72
            pixmap = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), colorspace=fitz.csGRAY)
            image = np.frombuffer(pixmap.samples, dtype=np.uint8).reshape(
                pixmap.height, pixmap.width
            )
            regions = self._detect_regions(image, zoom)
            return ViewDetectionResult(
                file_path=str(file_path), method="raster_segmentation", regions=regions
            )
        finally:
            document.close()

    def _detect_regions(self, image: np.ndarray, zoom: float) -> tuple[ViewRegion, ...]:
        _, binary = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        height_px, width_px = binary.shape
        # Рамка листа и боковая таблица изменений образуют один огромный
        # связный компонент и могут «приклеить» к себе главный вид.
        # Убираем только узкие стандартизованные поля по краям, не рабочее
        # поле чертежа.
        binary[: max(1, int(height_px * 0.02)), :] = 0
        binary[int(height_px * 0.76) :, :] = 0
        binary[:, : max(1, int(width_px * 0.07))] = 0
        binary[:, int(width_px * 0.99) :] = 0

        kernel_size = max(3, int(min(image.shape) * _DILATE_KERNEL_FRACTION))
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_size, kernel_size))
        dilated = cv2.dilate(binary, kernel, iterations=2)

        num_labels, _, stats, _ = cv2.connectedComponentsWithStats(dilated, connectivity=8)

        regions = []
        for label in range(1, num_labels):  # label 0 — фон
            x, y, w, h, area_px = stats[label]
            # Технические требования — широкий низкий текстовый блок над
            # штампом; общая шероховатость — компактная область в правом
            # верхнем углу. Оба объекта размечены отдельно и не являются
            # видами/разрезами/сечениями.
            is_technical_requirements = (
                x >= width_px * 0.45
                and y >= height_px * 0.55
                and w >= h * 2
            )
            is_general_roughness = (
                x >= width_px * 0.84
                and y <= height_px * 0.25
                and w <= width_px * 0.20
            )
            is_page_frame = w >= width_px * 0.95 or h >= height_px * 0.90
            if is_technical_requirements or is_general_roughness or is_page_frame:
                continue
            # Переводим обратно в пункты PDF (72 dpi), т.к. domain-модель
            # оперирует координатами листа, а не пикселями рендера.
            regions.append(
                ViewRegion(
                    x0=x / zoom, y0=y / zoom, x1=(x + w) / zoom, y1=(y + h) / zoom,
                    element_count=int(area_px),
                )
            )
        regions.sort(key=lambda r: r.area, reverse=True)

        if not regions:
            return ()
        largest_area = regions[0].area
        min_area = largest_area * _MIN_AREA_FRACTION_OF_LARGEST
        return tuple(r for r in regions if r.area >= min_area)

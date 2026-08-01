"""Доменные структуры результата детекции видов на поле чертежа
(Модуль 1.1: "извлечение данных с видов детали на поле чертежа")."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ViewRegion:
    """Обнаруженная область одного вида на листе чертежа (не сам вид как
    геометрия — просто ограничивающий прямоугольник и метрика плотности
    содержимого, достаточные, чтобы отделить виды друг от друга и от
    штампа/рамки/технических требований)."""

    x0: float
    y0: float
    x1: float
    y1: float
    element_count: int  # число векторных примитивов (линий/дуг) внутри области

    @property
    def width(self) -> float:
        return self.x1 - self.x0

    @property
    def height(self) -> float:
        return self.y1 - self.y0

    @property
    def area(self) -> float:
        return self.width * self.height


@dataclass(frozen=True)
class ViewDetectionResult:
    file_path: str
    method: str  # 'vector_clustering' | 'raster_segmentation'
    regions: tuple[ViewRegion, ...]

    @property
    def view_count(self) -> int:
        return len(self.regions)

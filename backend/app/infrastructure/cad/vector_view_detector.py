"""Детекция видов на чертеже путём пространственной кластеризации
векторных путей PDF (линии/дуги контуров).

Работает для векторных чертежей (все fixture в КД для тестов/ — такие).
Двухпроходный алгоритм без внешних ML-зависимостей:

1. Проход 1 — плотная кластеризация: боксы отдельных штрихов (линии,
   дуги, штриховка) объединяются в "протокластеры" фиксированным
   небольшим порогом (штрихи одного элемента чертежа расположены
   вплотную).
2. Проход 2 — укрупнение: протокластеры сливаются друг с другом порогом,
   пропорциональным их собственному размеру (min(диагональ_i, диагональ_j)
   * _MERGE_FRACTION). Это даёт устойчивость к разным масштабам/форматам
   листа (A4 vs A2) в отличие от фиксированного порога в пунктах PDF,
   который на разных чертежах давал от 2 до 36 кластеров вместо
   стабильных 2-6 реальных видов — см. эксперимент в истории разработки
   (dev/PROGRESS.md, Фаза 2 продолжение).

Область "вид" в этом определении — самодостаточный участок листа с одной
проекцией детали и её размерной сетью, а не только сам контур без
аннотаций (отделить контур от размеров средствами одной геометрии без
семантики невозможно, и для целей Модуля 1.1 не нужно — важно найти
сами зоны видов на поле чертежа, а не классифицировать линии внутри них).
"""

from __future__ import annotations

from pathlib import Path

import fitz

from app.domain.cad.view_detection_model import ViewDetectionResult, ViewRegion

# Проход 1: порог слияния отдельных штрихов в протокластер, в пунктах PDF.
_PASS1_MERGE_DISTANCE_PT = 15.0
_PASS1_MIN_ELEMENTS = 8

# Проход 2: доля от размера (диагонали) меньшего протокластера — во сколько
# раз область поиска соседа больше самого протокластера. Подобрано на 3
# реальных чертежах разного формата (A3, A2) — даёт стабильный результат
# в диапазоне 0.3-0.4, тогда как фиксированный порог в пунктах ломался при
# смене формата листа.
_PASS2_MERGE_FRACTION = 0.3

# Итоговые области меньше этой доли площади самой крупной области —
# шум (отдельные короткие штрихи, не образующие вид), не самостоятельный вид.
_MIN_AREA_FRACTION_OF_LARGEST = 0.001


class _UnionFind:
    def __init__(self, size: int) -> None:
        self._parent = list(range(size))

    def find(self, i: int) -> int:
        while self._parent[i] != i:
            self._parent[i] = self._parent[self._parent[i]]
            i = self._parent[i]
        return i

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self._parent[ra] = rb


def _grid_cluster(rects: list[fitz.Rect], threshold: float, min_elements: int) -> list[fitz.Rect]:
    """Кластеризация боксов с фиксированным порогом слияния через
    пространственную сетку (избегает O(n^2) сравнения каждый-с-каждым)."""
    n = len(rects)
    if n == 0:
        return []
    uf = _UnionFind(n)
    cell = max(threshold * 2, 1.0)
    grid: dict[tuple[int, int], list[int]] = {}
    for i, r in enumerate(rects):
        key = (int(r.x0 // cell), int(r.y0 // cell))
        grid.setdefault(key, []).append(i)

    for i, r in enumerate(rects):
        cx, cy = int(r.x0 // cell), int(r.y0 // cell)
        expanded = fitz.Rect(r.x0 - threshold, r.y0 - threshold, r.x1 + threshold, r.y1 + threshold)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for j in grid.get((cx + dx, cy + dy), []):
                    if j > i and expanded.intersects(rects[j]):
                        uf.union(i, j)

    groups: dict[int, list[int]] = {}
    for i in range(n):
        groups.setdefault(uf.find(i), []).append(i)

    clustered = []
    for indices in groups.values():
        if len(indices) < min_elements:
            continue
        cluster_rects = [rects[i] for i in indices]
        x0 = min(r.x0 for r in cluster_rects)
        y0 = min(r.y0 for r in cluster_rects)
        x1 = max(r.x1 for r in cluster_rects)
        y1 = max(r.y1 for r in cluster_rects)
        clustered.append(fitz.Rect(x0, y0, x1, y1))
    return clustered


def _merge_by_relative_distance(protoclusters: list[fitz.Rect], fraction: float) -> list[fitz.Rect]:
    """Второй проход: сливает протокластеры, если расстояние между ними
    меньше доли размера меньшего из них — устойчиво к масштабу листа."""
    n = len(protoclusters)
    if n <= 1:
        return protoclusters
    uf = _UnionFind(n)
    diagonals = [
        (r.width**2 + r.height**2) ** 0.5 for r in protoclusters
    ]
    for i in range(n):
        for j in range(i + 1, n):
            threshold = fraction * min(diagonals[i], diagonals[j])
            ri = protoclusters[i]
            expanded = fitz.Rect(
                ri.x0 - threshold, ri.y0 - threshold, ri.x1 + threshold, ri.y1 + threshold
            )
            if expanded.intersects(protoclusters[j]):
                uf.union(i, j)

    groups: dict[int, list[int]] = {}
    for i in range(n):
        groups.setdefault(uf.find(i), []).append(i)

    merged = []
    for indices in groups.values():
        cluster_rects = [protoclusters[i] for i in indices]
        x0 = min(r.x0 for r in cluster_rects)
        y0 = min(r.y0 for r in cluster_rects)
        x1 = max(r.x1 for r in cluster_rects)
        y1 = max(r.y1 for r in cluster_rects)
        merged.append(fitz.Rect(x0, y0, x1, y1))
    return merged


class VectorViewDetector:
    """Реализация IViewDetector для векторных PDF-чертежей."""

    def detect(self, file_path: Path) -> ViewDetectionResult:
        document = fitz.open(file_path)
        try:
            page = document[0]
            drawings = page.get_drawings()
            regions = self._detect_regions(drawings)
            return ViewDetectionResult(
                file_path=str(file_path), method="vector_clustering", regions=regions
            )
        finally:
            document.close()

    def _detect_regions(self, drawings: list[dict]) -> tuple[ViewRegion, ...]:
        if not drawings:
            return ()

        rects = [d["rect"] for d in drawings]
        protoclusters = _grid_cluster(rects, _PASS1_MERGE_DISTANCE_PT, _PASS1_MIN_ELEMENTS)
        if not protoclusters:
            return ()

        merged = _merge_by_relative_distance(protoclusters, _PASS2_MERGE_FRACTION)

        # element_count пересчитываем по числу исходных путей, реально
        # попавших в финальную область (а не по числу протокластеров).
        regions = []
        for area_rect in merged:
            count = sum(1 for r in rects if area_rect.intersects(r))
            regions.append(
                ViewRegion(
                    x0=area_rect.x0, y0=area_rect.y0, x1=area_rect.x1, y1=area_rect.y1,
                    element_count=count,
                )
            )
        regions.sort(key=lambda r: r.area, reverse=True)

        if not regions:
            return ()
        largest_area = regions[0].area
        min_area = largest_area * _MIN_AREA_FRACTION_OF_LARGEST
        return tuple(r for r in regions if r.area >= min_area)

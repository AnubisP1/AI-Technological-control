"""Порт сравнения фото изготовленного изделия с эталоном (Модуль 3.1).

Реализация — за интерфейсом в infrastructure (сейчас классическое CV
через OpenCV, см. docs/ARCHITECTURE.md) — можно заменить на более точный
алгоритм/модель, не меняя вызывающий код (KdReviewService-подобный
сервисный слой)."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from app.domain.quality_control.quality_model import PhotoComparisonResult


class IPhotoComparator(Protocol):
    def compare(self, reference_path: Path, actual_path: Path) -> PhotoComparisonResult: ...

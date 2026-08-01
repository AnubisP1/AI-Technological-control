"""Доменные структуры Модуля 3.1 (сравнение фото изготовленного изделия
с эталонным фото/изображением 3D-модели).

По ТЗ: "мы не сравниваем точно по миллиметрам геометрию, для
демонстрации работы достаточно будет просто сравнить по фото" — это
формально закрепляет модель как демонстрационную, не метрологическую.
Находки не выдумываются сверх того, что реально показали метрики
сравнения силуэта (см. photo_comparator.py) — при неуверенном результате
статус явно 'inconclusive', а не натянутое "брак"/"норма".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class QualityVerdict(str, Enum):
    OK = "ok"
    DEFECTIVE = "defective"
    INCONCLUSIVE = "inconclusive"
    """Сравнение не дало достаточно уверенного результата (напр. эталон
    и фото сильно отличаются по ракурсу/масштабу) — не выдаём "норма"
    или "брак" при недостаточных основаниях."""


@dataclass(frozen=True)
class DefectFinding:
    kind: str
    """Условная категория несоответствия силуэта: 'extra_region'
    (лишний выступ/область — кандидат на лишнее отверстие/выступ),
    'missing_region' (недостающая область — кандидат на непропечатанный/
    недоработанный участок), 'contour_mismatch' (общее несоответствие
    формы силуэта без точной локализации)."""

    description: str


@dataclass(frozen=True)
class PhotoComparisonResult:
    verdict: QualityVerdict
    similarity_score: float
    """0..1, метрика сходства силуэтов (не физическая точность) —
    см. photo_comparator.py за формулой."""
    findings: tuple[DefectFinding, ...] = field(default_factory=tuple)
    notes: tuple[str, ...] = field(default_factory=tuple)

"""Результат разбора комплекта КД (Модуль 1.1): чертёж + опциональная
3D-модель. Спецификация (BOM) сюда пока не входит — по ТЗ она нужна
только для металлических изделий и требует отдельного парсера состава
изделия, не реализованного на этой фазе (см. dev/PLAN.md Фаза 2)."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.cad.drawing_model import DrawingModel
from app.domain.cad.step_model import StepModel


@dataclass(frozen=True)
class KdAnalysisResult:
    drawing: DrawingModel | None
    step_model: StepModel | None

    @property
    def is_complete(self) -> bool:
        """И чертёж, и 3D-модель успешно разобраны."""
        return self.drawing is not None and self.step_model is not None

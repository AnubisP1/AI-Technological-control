"""Результат разбора комплекта КД (Модуль 1.1): чертёж (включая
детекцию видов) + опциональная 3D-модель. Спецификация (БОМ) сознательно
исключена из объёма проекта — по решению пользователя достаточно
чертежа и 3D-модели для формирования технологической документации
(dev/QUESTIONS.md обновлён соответствующим решением)."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.cad.drawing_model import DrawingModel
from app.domain.cad.step_model import StepModel
from app.domain.cad.view_detection_model import ViewDetectionResult


@dataclass(frozen=True)
class KdAnalysisResult:
    drawing: DrawingModel | None
    view_detection: ViewDetectionResult | None
    step_model: StepModel | None

    @property
    def is_complete(self) -> bool:
        """И чертёж, и 3D-модель успешно разобраны."""
        return self.drawing is not None and self.step_model is not None

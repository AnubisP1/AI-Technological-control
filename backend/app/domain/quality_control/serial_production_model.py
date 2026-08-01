"""Доменные структуры Модуля 3.2 — документы для запуска в серию
(случай качественного изделия) и рекомендации по устранению брака
(случай изделия с браком).

По решению пользователя (dev/QUESTIONS.md №8): метрики стоимости/рисков/
процента брака — демонстрационная эвристика (простые формулы от
количества операций/материала/типа детали + фиксированные коэффициенты
риска), явно помеченная как оценочная модель для демонстрации, а не
производственный расчёт. Это соответствует духу ТЗ для Модулей 3.2/4
("отображаем", "симулируем"), где прямо сказано не воспроизводить
реальный процесс.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SerialProductionPlan:
    """Демонстрационная оценка запуска в серию — не производственный
    расчёт, см. модуль docstring."""

    operation_count: int
    estimated_cycle_time_minutes: float
    estimated_batch_100_duration_days: float
    estimated_unit_cost_rub: float
    risk_level: str
    """'low'|'medium'|'high' — по фиксированным коэффициентам от числа
    операций и наличия warnings в автоподборе техпроцесса, не по
    статистике реального производства."""
    estimated_defect_rate_percent: float
    workshop_load_notes: tuple[str, ...] = field(default_factory=tuple)
    is_demonstration_estimate: bool = True


@dataclass(frozen=True)
class ProcessOptimizationSuggestion:
    text: str


@dataclass(frozen=True)
class DefectRemediationRecommendation:
    text: str


@dataclass(frozen=True)
class QualityReport:
    """Итоговый отчёт об оценке качества — формируется во всех случаях
    (и брак, и норма), см. ТЗ Модуль 3."""

    verdict: str
    similarity_score: float
    notes: tuple[str, ...]
    serial_production_plan: SerialProductionPlan | None = None
    optimization_suggestions: tuple[ProcessOptimizationSuggestion, ...] = field(default_factory=tuple)
    remediation_recommendations: tuple[DefectRemediationRecommendation, ...] = field(default_factory=tuple)

"""Сервис Модуля 3 — оценка качества по фото (3.1) и последующая
генерация документов (3.2): либо рекомендации по устранению брака, либо
документы для запуска в серию + рекомендации по оптимизации техпроцесса.
Отчёт об оценке качества формируется всегда, независимо от вердикта
(см. Техническое задание.md, раздел "Модуль 3").

Оценочная модель серийного плана — намеренно простая демонстрационная
эвристика (см. domain/quality_control/serial_production_model.py) —
не пытается быть точнее, чем позволяет доступный вход (число операций
автоподбора, наличие warnings).
"""

from __future__ import annotations

from pathlib import Path

from app.domain.manufacturing.simulation_model import SimulationPlan
from app.domain.quality_control.photo_comparator_port import IPhotoComparator
from app.domain.quality_control.quality_model import PhotoComparisonResult, QualityVerdict
from app.domain.quality_control.serial_production_model import (
    DefectRemediationRecommendation,
    ProcessOptimizationSuggestion,
    QualityReport,
    SerialProductionPlan,
)

_CYCLE_TIME_PER_OPERATION_MINUTES = 12.0
_UNIT_COST_PER_OPERATION_RUB = 350.0
_BASE_DEFECT_RATE_PERCENT = 2.0
_DEFECT_RATE_PER_WARNING_PERCENT = 1.5


class QualityControlService:
    def __init__(self, comparator: IPhotoComparator) -> None:
        self._comparator = comparator

    def assess(
        self,
        *,
        reference_photo_path: Path,
        actual_photo_path: Path,
        simulation_plan: SimulationPlan,
        planning_warnings: tuple[str, ...] = (),
    ) -> QualityReport:
        comparison = self._comparator.compare(reference_photo_path, actual_photo_path)

        if comparison.verdict is QualityVerdict.OK:
            plan = self._build_serial_production_plan(simulation_plan, planning_warnings)
            return QualityReport(
                verdict=comparison.verdict.value,
                similarity_score=comparison.similarity_score,
                notes=comparison.notes,
                serial_production_plan=plan,
                optimization_suggestions=self._build_optimization_suggestions(
                    simulation_plan, planning_warnings
                ),
            )

        if comparison.verdict is QualityVerdict.DEFECTIVE:
            return QualityReport(
                verdict=comparison.verdict.value,
                similarity_score=comparison.similarity_score,
                notes=comparison.notes,
                remediation_recommendations=self._build_remediation_recommendations(
                    simulation_plan
                ),
            )

        # INCONCLUSIVE — только отчёт, без ветвления в документы для серии
        # или в рекомендации по браку: неизвестно, к какой ветке относится.
        return QualityReport(
            verdict=comparison.verdict.value,
            similarity_score=comparison.similarity_score,
            notes=comparison.notes,
        )

    def _build_serial_production_plan(
        self, simulation_plan: SimulationPlan, warnings: tuple[str, ...]
    ) -> SerialProductionPlan:
        operation_count = len(simulation_plan.operations)
        cycle_time = operation_count * _CYCLE_TIME_PER_OPERATION_MINUTES
        unit_cost = operation_count * _UNIT_COST_PER_OPERATION_RUB
        batch_100_days = round((cycle_time * 100) / (60 * 8), 1)  # при смене 8ч

        risk_level = "low"
        if warnings:
            risk_level = "high" if len(warnings) > 1 else "medium"

        defect_rate = _BASE_DEFECT_RATE_PERCENT + len(warnings) * _DEFECT_RATE_PER_WARNING_PERCENT

        workshop_notes = (
            (
                f"Автоподбор техпроцесса вернул {len(warnings)} предупреждени(е/я) — "
                "заложено в повышенную оценку риска и процента брака ниже.",
            )
            if warnings
            else ("Автоподбор техпроцесса прошёл без замечаний.",)
        )

        return SerialProductionPlan(
            operation_count=operation_count,
            estimated_cycle_time_minutes=round(cycle_time, 1),
            estimated_batch_100_duration_days=batch_100_days,
            estimated_unit_cost_rub=round(unit_cost, 2),
            risk_level=risk_level,
            estimated_defect_rate_percent=round(defect_rate, 1),
            workshop_load_notes=workshop_notes,
        )

    def _build_optimization_suggestions(
        self, simulation_plan: SimulationPlan, warnings: tuple[str, ...]
    ) -> tuple[ProcessOptimizationSuggestion, ...]:
        suggestions = []
        if simulation_plan.material_kind == "metal" and len(simulation_plan.operations) > 3:
            suggestions.append(
                ProcessOptimizationSuggestion(
                    "Рассмотреть объединение операций на одном станке с ЧПУ "
                    "(если позволяет парк оборудования) для сокращения числа переустановов."
                )
            )
        if simulation_plan.material_kind == "plastic":
            suggestions.append(
                ProcessOptimizationSuggestion(
                    "Оценить возможность печати партией на нескольких принтерах "
                    "параллельно для сокращения общего времени цикла серии."
                )
            )
        if warnings:
            suggestions.append(
                ProcessOptimizationSuggestion(
                    "Устранить замечания автоподбора техпроцесса (см. предупреждения "
                    "маршрутной карты) до запуска в серию — они повышают расчётный риск."
                )
            )
        if not suggestions:
            suggestions.append(
                ProcessOptimizationSuggestion(
                    "Существенных точек оптимизации автоподбор не выявил — техпроцесс "
                    "признан приемлемым для демонстрационной оценки."
                )
            )
        return tuple(suggestions)

    def _build_remediation_recommendations(
        self, simulation_plan: SimulationPlan
    ) -> tuple[DefectRemediationRecommendation, ...]:
        if simulation_plan.material_kind == "plastic":
            return (
                DefectRemediationRecommendation(
                    "Проверить параметры печати (высота слоя, скорость, температура) "
                    "и калибровку стола — расхождение силуэта с эталоном на печатных "
                    "изделиях часто связано с отслоением или деформацией при печати."
                ),
                DefectRemediationRecommendation(
                    "Сверить постобработку с картой (см. Модуль 1.3) — пропущенный "
                    "обязательный шаг может изменить форму детали относительно эталона."
                ),
            )
        return (
            DefectRemediationRecommendation(
                "Проверить настройку оборудования и режимы обработки на операциях "
                "перед той, где предположительно возникло отклонение формы."
            ),
            DefectRemediationRecommendation(
                "Сверить фактически использованную оснастку с маршрутной картой "
                "(Модуль 1.3) — несоответствие оснастки — частая причина лишних "
                "или недостающих элементов геометрии."
            ),
        )

"""Расчёт режимов резания (V/S/t/n) для операций металлообработки —
Фаза 17, по явному запросу пользователя ("нужен точный расчёт по
режимам резания", 2026-08-03).

Формула скорости резания — классическая эмпирическая зависимость из
Справочника технолога-машиностроителя (Косилова/Мещерякова):
    V = Cv / (T^m * t^xv * S^yv) * Kv
где Kv в этой модели — коэффициент обрабатываемости материала
(material_group.machinability_index), т.к. это единственный источник
относительной обрабатываемости в проекте (см. Фазы 0-4) — не заводим
второй, дублирующий коэффициент.

Подача (S) и глубина резания (t) берутся серединой табличного диапазона
(feed_reference) — на практике технолог выбирает конкретное значение по
шероховатости/припуску чертежа, чего упрощённый автоподбор не делает;
середина диапазона — нейтральная оценка, не выдуманное число.

Машинное время (То) не рассчитывается: требует длины прохода резания,
которая зависит от конкретного участка детали (не от диаметра заготовки
и не от типоразмера проката) — эта информация недоступна упрощённому
автоподбору (нет геометрии детали, см. dev/PROGRESS.md Фаза 4). Явно
не рассчитывается, а не подставляется приблизительно.
"""

from __future__ import annotations

import math

from app.domain.process_planning.cutting_mode_model import CuttingModeResult
from app.domain.process_planning.process_planning_lookup_port import IProcessPlanningLookup


class CuttingModeCalculator:
    def __init__(self, lookup: IProcessPlanningLookup) -> None:
        self._lookup = lookup

    def calculate(
        self,
        *,
        operation_type_id: int,
        operation_type_code: str,
        material_group_id: int,
        blank_diameter_mm: float | None,
        spindle_speed_min_rpm: int | None,
        spindle_speed_max_rpm: int | None,
    ) -> CuttingModeResult:
        if blank_diameter_mm is None:
            return CuttingModeResult(
                operation_type_code=operation_type_code,
                is_calculated=False,
                source_note=(
                    "Диаметр заготовки не распознан на чертеже — расчёт режимов "
                    "резания невозможен без диаметра."
                ),
            )

        formula = self._lookup.find_cutting_mode_formula(operation_type_id)
        if formula is None:
            return CuttingModeResult(
                operation_type_code=operation_type_code,
                is_calculated=False,
                source_note=(
                    f"Для операции '{operation_type_code}' в справочнике нет "
                    "коэффициентов формулы режимов резания."
                ),
            )

        feed_ref = self._lookup.find_feed_reference(operation_type_id, material_group_id)
        if feed_ref is None:
            return CuttingModeResult(
                operation_type_code=operation_type_code,
                is_calculated=False,
                source_note=(
                    f"Для операции '{operation_type_code}' и данной группы материала "
                    "в справочнике нет типовой подачи/глубины резания."
                ),
            )

        machinability = self._lookup.find_material_machinability(material_group_id)
        kv = machinability.machinability_index if machinability is not None else 1.0

        feed_mm_rev = (feed_ref.feed_mm_rev_min + feed_ref.feed_mm_rev_max) / 2

        is_drilling = operation_type_code == "DRILL"
        if is_drilling:
            # Глубина резания при сверлении сплошного отверстия равна
            # половине диаметра инструмента — берём диаметр заготовки как
            # приближение диаметра сверла (упрощённый автоподбор не знает
            # диаметр отверстия отдельно от диаметра детали).
            depth_of_cut_mm = blank_diameter_mm / 2
        elif feed_ref.depth_of_cut_mm_min is not None and feed_ref.depth_of_cut_mm_max is not None:
            depth_of_cut_mm = (feed_ref.depth_of_cut_mm_min + feed_ref.depth_of_cut_mm_max) / 2
        else:
            return CuttingModeResult(
                operation_type_code=operation_type_code,
                is_calculated=False,
                source_note=(
                    f"Для операции '{operation_type_code}' в справочнике нет "
                    "диапазона глубины резания."
                ),
            )

        cutting_speed_m_min = (
            formula.cv
            / (
                formula.tool_life_min**formula.m
                * depth_of_cut_mm**formula.xv
                * feed_mm_rev**formula.yv
            )
            * kv
        )

        spindle_speed_rpm = 1000 * cutting_speed_m_min / (math.pi * blank_diameter_mm)
        if spindle_speed_min_rpm is not None and spindle_speed_max_rpm is not None:
            spindle_speed_rpm = max(spindle_speed_min_rpm, min(spindle_speed_max_rpm, spindle_speed_rpm))
            # Фактическая скорость резания пересчитывается назад по
            # округлённым до реального диапазона станка оборотам — иначе
            # V в отчёте не соответствовал бы реально достижимым n на этом
            # оборудовании.
            cutting_speed_m_min = math.pi * blank_diameter_mm * spindle_speed_rpm / 1000

        return CuttingModeResult(
            operation_type_code=operation_type_code,
            is_calculated=True,
            cutting_speed_m_min=round(cutting_speed_m_min, 1),
            spindle_speed_rpm=round(spindle_speed_rpm),
            feed_mm_rev=round(feed_mm_rev, 3),
            depth_of_cut_mm=round(depth_of_cut_mm, 2),
            machining_time_min=None,
            source_note=f"{formula.source}; {feed_ref.source}",
        )

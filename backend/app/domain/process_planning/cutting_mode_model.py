"""Доменная структура результата расчёта режимов резания (Фаза 17) —
V/S/t/n/То по эмпирическим формулам Справочника технолога-
машиностроителя (см. seed_cutting_modes.sql). Не заменяет полноценное
технологическое проектирование — рассчитывает по одному представительному
режиму на операцию (не по каждому переходу с разными припусками),
явно фиксируя источник и то, был ли расчёт вообще возможен.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CuttingModeResult:
    operation_type_code: str
    is_calculated: bool
    cutting_speed_m_min: float | None = None
    spindle_speed_rpm: int | None = None
    feed_mm_rev: float | None = None
    depth_of_cut_mm: float | None = None
    machining_time_min: float | None = None
    source_note: str = ""

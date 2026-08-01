"""Доменные структуры техпроцесса, автоматически подобранного по
простым правилам (Модуль 1.3, упрощённый автоподбор — см. dev/PLAN.md
Фаза 4). Не заменяет полноценное технологическое проектирование —
подбор по совместимости из БД НСИ (equipment_type_material_group и
т.д.), без расчёта режимов резания и без учёта конкретной геометрии
детали кроме габаритов.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PlannedOperation:
    """Одна операция подобранного техпроцесса — строка маршрутной карты."""

    sequence_no: int
    operation_type_code: str
    operation_type_name: str
    equipment_type_code: str
    equipment_model_name: str | None  # None, если подходящая модель не найдена в справочнике
    tooling_names: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ProcessPlanningResult:
    """Результат автоподбора техпроцесса — то, из чего строится
    маршрутная карта (Модуль 1.3)."""

    part_name: str | None
    material_grade: str | None
    workpiece_type_name: str | None
    operations: tuple[PlannedOperation, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)

    @property
    def is_empty(self) -> bool:
        return len(self.operations) == 0

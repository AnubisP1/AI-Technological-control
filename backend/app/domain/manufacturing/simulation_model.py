"""Доменная модель симуляции изготовления (Модуль 2).

По ТЗ это не управление реальным оборудованием, а UI-имитация: для
каждой операции маршрутной/техпроцессной карты показывается условное
время выполнения, статичная картинка (референс) используемого станка/
принтера и построчная имитация генерации управляющей программы —
заранее подготовленный универсальный текст программы, а не результат
реального постпроцессора. Общая длительность шкалы прогресса
фиксирована ТЗ — 15 секунд на весь процесс, время операций
распределяется пропорционально внутри этого окна на стороне фронтенда.
"""

from __future__ import annotations

from dataclasses import dataclass, field

TOTAL_SIMULATION_SECONDS = 15


@dataclass(frozen=True)
class SimulatedOperation:
    sequence_no: int
    name: str
    machine_icon: str
    """Код упрощённой категории для статичной SVG-иконки на фронтенде
    (напр. 'lathe', 'mill', 'drill', 'grind', 'control', 'fdm_printer',
    'resin_printer', 'sls_printer') — см. ICON по operation/printer type
    code в manufacturing_simulation_service.py."""
    machine_label: str
    program_lines: tuple[str, ...] = field(default_factory=tuple)
    duration_share: float = 1.0
    """Доля от TOTAL_SIMULATION_SECONDS — операции распределяются
    пропорционально этой доле, а не в абсолютных секундах, чтобы сумма
    времён всегда давала ровно TOTAL_SIMULATION_SECONDS вне зависимости
    от числа операций в конкретной карте."""


@dataclass(frozen=True)
class SimulationPlan:
    part_name: str | None
    material_kind: str
    """'metal' | 'plastic' — определяет, какой универсальный шаблон
    управляющей программы используется (NC G-code для станков,
    слайсер-подобный G-code для 3D-печати)."""
    operations: tuple[SimulatedOperation, ...]
    total_seconds: int = TOTAL_SIMULATION_SECONDS

    @property
    def is_empty(self) -> bool:
        return len(self.operations) == 0

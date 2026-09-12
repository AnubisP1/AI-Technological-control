"""Порт доступа к нормативным требованиям ГОСТ ЕСКД, нужным для проверки
оформления чертежа (Модуль 1.2).

Отделён от `nsi_lookup_port.py` намеренно: тот отвечает на вопрос «есть ли
такой материал/заготовка на предприятии» (справочник ресурсов), а этот —
«оформлен ли чертёж по правилам» (нормативные требования). Это разные
источники (`БД НСИ/schema/` против `БД НСИ/ГОСТ/schema/`) и разные
основания для находок в отчёте.

Возвращаются только те виды требований, которые реально проверяются
автоматически: числовые границы, закрытые перечни значений и графы
основной надписи. Пункты типа PROCEDURAL из БД сюда не попадают — по ним
нельзя вынести однозначный вердикт, и делать вид, что можно, было бы
хуже, чем честно их не проверять.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class GostEnumRequirement:
    """Требование вида «значение должно быть из закрытого перечня»
    (requirement_type = 'ENUM_CHOICE' с заполненным allowed_values)."""

    standard_designation: str  # 'ГОСТ 2.302-1968'
    clause_number: str  # '2-умен'
    parameter_name: str  # 'масштаб уменьшения (допустимый ряд)'
    allowed_values: tuple[str, ...]
    clause_text: str


@dataclass(frozen=True)
class GostNumericRequirement:
    """Требование вида «значение должно укладываться в числовую границу»
    (requirement_type = 'NUMERIC_LIMIT')."""

    standard_designation: str
    clause_number: str
    parameter_name: str
    unit: str | None
    comparison_op: str  # '<=', '<', '=', '>=', '>', 'BETWEEN'
    limit_value_min: float | None
    limit_value_max: float | None
    clause_text: str


@dataclass(frozen=True)
class GostTitleBlockField:
    """Графа основной надписи по ГОСТ Р 2.104 (таблица 1).

    required_paper/required_electronic хранят условные обозначения самого
    стандарта: '●' обязательна, '○' зависит от вида КД и условий,
    '*' не обязательна. Не сводим их к булеву флагу — потеряется
    различие «нарушение» и «требует уточнения»."""

    standard_designation: str
    field_number: str  # '1', '3', '32'
    field_heading: str | None  # 'Масса', 'Масштаб'; None если графа без заголовка
    content_kind: str | None  # 'Реквизит КД «Наименование»'
    fill_rule: str
    required_paper: str | None
    required_electronic: str | None


class IGostLookup(Protocol):
    def find_enum_requirements(self) -> tuple[GostEnumRequirement, ...]: ...
    def find_numeric_requirements(self) -> tuple[GostNumericRequirement, ...]: ...
    def find_title_block_fields(self) -> tuple[GostTitleBlockField, ...]: ...

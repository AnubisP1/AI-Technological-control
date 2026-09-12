"""Порт доступа к типовым формулировкам технических требований
(ОСТ 1 02504-84) для проверки КД (Модуль 1.2).

Отделён от nsi_lookup_port намеренно: тот отвечает на вопрос «есть ли
такой материал/заготовка на предприятии», а этот — «совпадает ли
формулировка пункта ТТ с типовой, установленной отраслевым
стандартом». Разные источники и разные основания для находок.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class TypicalRequirementTemplate:
    """Типовая формулировка ТТ дословно из таблиц ОСТ 1 02504-84.

    В шаблоне сохранены прочерки-поля источника («HRC ___»): они
    показывают, что конструктор обязан подставить конкретное значение,
    и при сопоставлении с реальным пунктом чертежа игнорируются.
    """

    code: str
    formulation_template: str
    reference_standard: str | None
    notes: str | None


class ITypicalRequirementLookup(Protocol):
    def find_typical_requirements(self) -> tuple[TypicalRequirementTemplate, ...]: ...

"""Доменные структуры результата сверки КД с БД НСИ (Модуль 1.2).

По ТЗ Модуль 1.2 оценивает: (1) корректность технических требований,
(2) доступность материала, указанного в заготовке, (3) формирует
обратную связь на этап проектирования при невозможности изготовления/
высоком риске брака/более эффективном варианте. Три раздела ниже
соответствуют этим трём пунктам напрямую.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class MatchStatus(str, Enum):
    """Статус сопоставления одного проверяемого факта с НСИ.
    NOT_FOUND — не выдумываем совпадение, если его нет в справочнике."""

    MATCHED = "matched"
    PARTIAL_MATCH = "partial_match"  # напр. ГОСТ совпал, конкретный типоразмер — нет
    NOT_FOUND = "not_found"


@dataclass(frozen=True)
class MaterialCheck:
    """Проверка доступности материала, указанного на чертеже, в справочнике НСИ."""

    material_from_drawing: str | None
    status: MatchStatus
    matched_grade: str | None = None
    matched_gost: str | None = None
    note: str = ""


@dataclass(frozen=True)
class BlankCheck:
    """Проверка заготовки (workpiece_blank), указанной на чертеже, в справочнике НСИ."""

    blank_from_drawing: str | None
    status: MatchStatus
    matched_designation: str | None = None
    note: str = ""


@dataclass(frozen=True)
class TechnicalRequirementCheck:
    """Оценка одного пункта технических требований чертежа."""

    number: int
    text: str
    is_recognized: bool  # удалось ли сопоставить пункт с известной категорией ТТ
    category: str | None  # напр. 'hardness', 'coating', 'roughness' — см. tt_categories.py
    note: str = ""


@dataclass(frozen=True)
class KdReviewFinding:
    """Одна находка обратной связи на этап проектирования — конкретная,
    не общая фраза, чтобы конструктор понимал, что именно исправить."""

    severity: str  # 'blocking' | 'warning' | 'info'
    message: str


@dataclass(frozen=True)
class KdReviewReport:
    """Итоговый отчёт об оценке КД по результатам сверки с БД НСИ."""

    material_check: MaterialCheck | None
    blank_check: BlankCheck | None
    technical_requirement_checks: tuple[TechnicalRequirementCheck, ...] = field(default_factory=tuple)
    findings: tuple[KdReviewFinding, ...] = field(default_factory=tuple)

    @property
    def has_blocking_findings(self) -> bool:
        return any(f.severity == "blocking" for f in self.findings)

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
    # Сверка формулировки с типовой по ОСТ 1 02504-84 (табл. 11).
    # None означает «типовая формулировка не найдена» — это НЕ нарушение:
    # стандарт не запрещает формулировать иначе, если требование понятно.
    typical_template_code: str | None = None
    typical_formulation: str | None = None
    typical_reference_standard: str | None = None


class GostCheckStatus(str, Enum):
    """Результат проверки одного требования ГОСТ к оформлению чертежа.

    NOT_APPLICABLE и NEEDS_REVIEW различаются намеренно: первое — правило
    к этому чертежу не относится, второе — относится, но однозначный
    вердикт машина вынести не может (графа с обязательностью «○» по
    ГОСТ 2.104 — зависит от вида КД). Схлопывать их в «ок» нельзя: это
    скрыло бы от технолога места, требующие его решения."""

    PASSED = "passed"
    VIOLATED = "violated"
    NEEDS_REVIEW = "needs_review"
    NOT_APPLICABLE = "not_applicable"


@dataclass(frozen=True)
class GostRequirementCheck:
    """Проверка одного требования ГОСТ к оформлению чертежа.

    Всегда несёт ссылку на конкретный пункт стандарта — технолог должен
    видеть основание вердикта, а не только сам вердикт."""

    standard_designation: str  # 'ГОСТ 2.302-1968'
    clause_number: str  # '2-умен', '6.3', 'графа 3'
    parameter_name: str  # что проверялось
    status: GostCheckStatus
    actual_value: str | None = None  # что фактически найдено на чертеже
    expected: str | None = None  # чего требует стандарт
    note: str = ""


@dataclass(frozen=True)
class KdReviewFinding:
    """Одна находка обратной связи на этап проектирования — конкретная,
    не общая фраза, чтобы конструктор понимал, что именно исправить."""

    severity: str  # 'blocking' | 'warning' | 'info'
    message: str


@dataclass(frozen=True)
class ReviewSummary:
    """Связное текстовое резюме отчёта — отдельно от структурных находок,
    см. domain/kd_review/text_generator_port.py."""

    text: str
    generated_by: str  # 'llm' | 'template'


@dataclass(frozen=True)
class KdReviewReport:
    """Итоговый отчёт об оценке КД по результатам сверки с БД НСИ."""

    material_check: MaterialCheck | None
    blank_check: BlankCheck | None
    technical_requirement_checks: tuple[TechnicalRequirementCheck, ...] = field(default_factory=tuple)
    # Проверка оформления чертежа по ГОСТ ЕСКД (БД НСИ/ГОСТ/) — отдельный
    # раздел отчёта: сверка с НСИ отвечает «есть ли такой материал на
    # предприятии», а эти проверки — «оформлен ли чертёж по правилам».
    # Пустой кортеж, если база ГОСТ недоступна: отсутствие проверок не
    # выдаётся за их успешное прохождение.
    gost_checks: tuple[GostRequirementCheck, ...] = field(default_factory=tuple)
    findings: tuple[KdReviewFinding, ...] = field(default_factory=tuple)
    summary: ReviewSummary | None = None

    @property
    def has_blocking_findings(self) -> bool:
        return any(f.severity == "blocking" for f in self.findings)

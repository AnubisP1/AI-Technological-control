"""Доменная модель согласования комплекта ТД главным технологом
(Модуль 2, см. Техническое задание.md раздел "Модуль 2: Контроль и
исполнение").

Согласование в этой системе не хранится персистентно (нет БД проектов/
заявок в архитектуре) — это разовое решение пользователя в рамках одной
сессии работы с уже сгенерированным комплектом документов из Модуля 1.
При отклонении пользователь возвращается к Модулю 1 для повторной
генерации с учётом комментария — сам комментарий не интерпретируется
системой автоматически (нет ML/LLM-компонента, который бы правил карту
по тексту комментария), он адресован человеку, который перезапускает
генерацию.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ApprovalDecision(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass(frozen=True)
class ApprovalResult:
    decision: ApprovalDecision
    comment: str | None

    @property
    def can_start_simulation(self) -> bool:
        return self.decision is ApprovalDecision.APPROVED

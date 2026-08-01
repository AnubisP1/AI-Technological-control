"""Сервис согласования комплекта ТД (Модуль 2, первый шаг).

Не хранит решение — по архитектуре проекта нет персистентного стора
проектов/заявок (см. dev/docs/ARCHITECTURE.md), согласование живёт в
рамках одной сессии работы пользователя с фронтендом: подтвердил —
пошёл в симуляцию; отклонил — вернулся в Модуль 1 с комментарием для
повторной генерации.
"""

from __future__ import annotations

from app.domain.manufacturing.approval_model import ApprovalDecision, ApprovalResult


class ApprovalRejectionRequiresCommentError(ValueError):
    pass


class ApprovalService:
    def decide(self, *, decision: ApprovalDecision, comment: str | None) -> ApprovalResult:
        normalized_comment = comment.strip() if comment else None
        if decision is ApprovalDecision.REJECTED and not normalized_comment:
            raise ApprovalRejectionRequiresCommentError(
                "При отклонении комплекта ТД необходимо указать комментарий "
                "для повторной генерации главным технологом."
            )
        return ApprovalResult(decision=decision, comment=normalized_comment)

import pytest

from app.domain.manufacturing.approval_model import ApprovalDecision
from app.services.approval_service import ApprovalRejectionRequiresCommentError, ApprovalService


def test_approve_without_comment_succeeds():
    service = ApprovalService()
    result = service.decide(decision=ApprovalDecision.APPROVED, comment=None)

    assert result.can_start_simulation is True
    assert result.comment is None


def test_reject_with_comment_succeeds():
    service = ApprovalService()
    result = service.decide(
        decision=ApprovalDecision.REJECTED, comment="Не указан разряд оператора"
    )

    assert result.can_start_simulation is False
    assert result.comment == "Не указан разряд оператора"


def test_reject_without_comment_raises():
    """Отклонение без комментария не несёт технологу информации, что
    исправлять при повторной генерации, поэтому запрещено на уровне
    сервиса, а не только UI-валидацией."""
    service = ApprovalService()

    with pytest.raises(ApprovalRejectionRequiresCommentError):
        service.decide(decision=ApprovalDecision.REJECTED, comment=None)


def test_reject_with_blank_comment_raises():
    service = ApprovalService()

    with pytest.raises(ApprovalRejectionRequiresCommentError):
        service.decide(decision=ApprovalDecision.REJECTED, comment="   ")

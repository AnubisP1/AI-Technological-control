"""Порт генерации связного текстового резюме отчёта КД (Модуль 1.2,
Фаза 8 — см. dev/QUESTIONS.md №12).

Структурированные находки (KdReviewFinding, TechnicalRequirementCheck и
т.д.) остаются машиночитаемыми и не зависят от этого порта — дерево
проверок и цветовая раскраска на фронтенде строятся из них напрямую.
ITextGenerator отвечает только за отдельный связный абзац-резюме поверх
уже готовых фактов, не подменяет и не изменяет сами факты — генератор
не может "придумать" находку, которой нет в переданных данных.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class GeneratedText:
    text: str
    generated_by: str
    """'llm' | 'template' — какой путь реально сработал. UI и API-ответ
    обязаны показывать это поле, чтобы не выдавать шаблонный текст за
    результат LLM и наоборот (см. QUESTIONS.md №12)."""


class ITextGenerator(Protocol):
    def summarize_review(self, *, facts: dict) -> GeneratedText: ...

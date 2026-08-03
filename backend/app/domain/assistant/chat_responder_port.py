"""Порт AI-ассистента по вопросам НСИ/технологичности (Модуль 1,
Фаза 15/17 часть 5 — по прямому запросу пользователя, экран "Обзор").

Тот же принцип, что и ITextGenerator (см. domain/kd_review/text_generator_port.py):
контекстные факты собираются вызывающим кодом (keyword-поиск по
справочникам НСИ, см. AssistantService) и передаются генератору как
готовые данные — ChatResponder не может "придумать" факт о справочнике,
которого нет в переданном контексте, только сформулировать связный
ответ на естественном языке поверх уже найденного.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ChatReply:
    text: str
    generated_by: str
    """'llm' | 'template' — какой путь реально сработал, как и в
    ReviewSummary — UI обязан показывать источник ответа."""


class IChatResponder(Protocol):
    def reply(self, *, question: str, context_facts: dict) -> ChatReply: ...

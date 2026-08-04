"""Композитная реализация IChatResponder — аналог ChainedTextGenerator
для AssistantService (см. его docstring для полного контекста решения)."""

from __future__ import annotations

import logging

from app.domain.assistant.chat_responder_port import ChatReply, IChatResponder

logger = logging.getLogger(__name__)


class ChainedChatResponder:
    def __init__(self, providers: tuple[IChatResponder, ...]) -> None:
        if not providers:
            raise ValueError("ChainedChatResponder требует хотя бы одного провайдера")
        self._providers = providers

    def reply(self, *, question: str, context_facts: dict) -> ChatReply:
        last_error: Exception | None = None
        for provider in self._providers:
            try:
                return provider.reply(question=question, context_facts=context_facts)
            except Exception as exc:
                logger.warning(
                    "Чат-провайдер %s недоступен, пробуем следующий в цепочке",
                    type(provider).__name__,
                    exc_info=True,
                )
                last_error = exc
        assert last_error is not None
        raise last_error

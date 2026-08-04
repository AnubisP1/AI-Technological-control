"""Композитная реализация ITextGenerator, пробующая несколько реальных
LLM-провайдеров по приоритету (Фаза 18, часть 2 — Polza.ai + локальный
Qwen работают параллельно, см. dev/QUESTIONS.md №15).

Не заменяет фолбэк на TemplateTextGenerator — тот остаётся в
KdReviewService._summarize() как последний рубеж. ChainedTextGenerator
лишь пробует провайдеров ПЕРЕД шаблоном: первый успешный ответ
возвращается сразу, ошибка каждого логируется и провоцирует переход к
следующему; если все провайдеры не сработали — поднимается исключение
последнего, которое KdReviewService уже умеет ловить.
"""

from __future__ import annotations

import logging

from app.domain.kd_review.text_generator_port import GeneratedText, ITextGenerator

logger = logging.getLogger(__name__)


class ChainedTextGenerator:
    def __init__(self, providers: tuple[ITextGenerator, ...]) -> None:
        if not providers:
            raise ValueError("ChainedTextGenerator требует хотя бы одного провайдера")
        self._providers = providers

    def summarize_review(self, *, facts: dict) -> GeneratedText:
        last_error: Exception | None = None
        for provider in self._providers:
            try:
                return provider.summarize_review(facts=facts)
            except Exception as exc:
                logger.warning(
                    "LLM-провайдер %s недоступен, пробуем следующий в цепочке",
                    type(provider).__name__,
                    exc_info=True,
                )
                last_error = exc
        assert last_error is not None
        raise last_error

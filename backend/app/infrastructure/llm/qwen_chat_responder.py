"""Реализация IChatResponder через локальный Qwen2.5-7B-Instruct (GGUF,
llama-cpp-python) — Фаза 18, заменяет прежний облачный
YandexGptChatResponder (см. dev/QUESTIONS.md №14). Полностью офлайн,
используется AssistantService (чат на экране "Обзор").

Работает параллельно с облачным PolzaChatResponder (Фаза 18, часть 2, см.
dev/QUESTIONS.md №15) — оба реализуют один порт с общим промптом
(assistant_chat_prompt.py); _build_chat_responder() в routes.py выбирает
между ними по приоритету (Polza.ai первым, локальный Qwen — фолбэком).

Модели запрещено отвечать на основании собственных общих знаний вне
переданного контекста — системный промпт явно требует опираться только
на найденные факты, чтобы не выдавать выдуманные марки/ГОСТы/режимы за
содержимое локальной базы.

Выполняется через run_heavy() (см. qwen_text_generator.py) — та же
причина: CPU-инференс не должен блокировать event loop FastAPI.
"""

from __future__ import annotations

from pathlib import Path

from app.domain.assistant.chat_responder_port import ChatReply
from app.infrastructure.llm.assistant_chat_prompt import SYSTEM_PROMPT, build_user_prompt
from app.infrastructure.llm.llama_cpp_engine import get_engine

_MAX_TOKENS = 400
_TEMPERATURE = 0.2


class QwenChatResponder:
    def __init__(self, model_path: Path, context_size: int) -> None:
        self._model_path = model_path
        self._context_size = context_size

    def reply(self, *, question: str, context_facts: dict) -> ChatReply:
        engine = get_engine(self._model_path, self._context_size)
        text = engine.complete(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=build_user_prompt(question, context_facts),
            max_tokens=_MAX_TOKENS,
            temperature=_TEMPERATURE,
        )
        return ChatReply(text=text, generated_by="llm")

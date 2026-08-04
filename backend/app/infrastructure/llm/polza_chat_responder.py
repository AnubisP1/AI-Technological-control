"""Реализация IChatResponder через облачный Polza.ai (OpenAI-совместимый
API) — Фаза 18, часть 2 (см. dev/QUESTIONS.md №15). Тот же осознанный
повторный сетевой путь, что PolzaTextGenerator — см. его docstring для
полного контекста решения (параллельно локальному Qwen, не замена).

Требует сети и ключа API (POLZA_API_KEY в .env) — при их отсутствии или
ошибке вызывающий код обязан откатиться на следующий провайдер в цепочке
(локальный Qwen, затем шаблон), не падать (см. AssistantService).

Модель — параметр конструктора, не константа (см. PolzaTextGenerator —
тот же ключ может не иметь доступа к произвольной модели каталога).
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request

from app.domain.assistant.chat_responder_port import ChatReply
from app.infrastructure.llm.assistant_chat_prompt import SYSTEM_PROMPT, build_user_prompt

_COMPLETION_URL = "https://polza.ai/api/v1/chat/completions"
_REQUEST_TIMEOUT_SECONDS = 30
_MAX_TOKENS = 400
_TEMPERATURE = 0.2


class PolzaApiError(RuntimeError):
    pass


class PolzaChatResponder:
    def __init__(self, api_key: str, model: str) -> None:
        self._api_key = api_key
        self._model = model

    def reply(self, *, question: str, context_facts: dict) -> ChatReply:
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_user_prompt(question, context_facts)},
            ],
            "temperature": _TEMPERATURE,
            "max_tokens": _MAX_TOKENS,
        }

        request = urllib.request.Request(
            _COMPLETION_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._api_key}",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=_REQUEST_TIMEOUT_SECONDS) as response:
                body = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError) as exc:
            raise PolzaApiError(f"Сетевая ошибка обращения к Polza.ai API: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise PolzaApiError(f"Некорректный ответ Polza.ai API: {exc}") from exc

        try:
            text = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as exc:
            raise PolzaApiError(f"Неожиданный формат ответа Polza.ai API: {body}") from exc

        return ChatReply(text=text.strip(), generated_by="llm")

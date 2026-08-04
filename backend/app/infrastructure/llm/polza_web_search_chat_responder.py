"""Реализация IChatResponder через облачный Polza.ai с включённым
веб-поиском (`plugins: [{"id": "web"}]`, см. https://polza.ai/docs/gaidy/web-search) —
Фаза 21, по прямому запросу пользователя: "ответы на вопросы которые
пользователь задает ассистенту можешь искать в интернете через polza
если нет информации в БД НСИ".

⚠️ ОТДЕЛЬНЫЙ, БОЛЕЕ СЛАБЫЙ УРОВЕНЬ ДОСТОВЕРНОСТИ, ЧЕМ ОСТАЛЬНЫЕ
ПРОВАЙДЕРЫ ЭТОГО ПОРТА. `PolzaChatResponder`/`QwenChatResponder` строго
ограничены переданными фактами НСИ — этот класс сознательно снимает то
же ограничение и разрешает модели использовать общедоступные веб-данные,
т.к. цель — ответить хоть что-то полезное, когда в локальной БД НСИ
ответа нет. НЕ используется, если keyword-поиск нашёл совпадения в
НСИ — вызывающий код (AssistantService.ask()) обязан включать этот
провайдер ТОЛЬКО когда context_facts["matches"] пусто, иначе модель
может предпочесть менее надёжный интернет-источник реальным данным
локальной базы, которые уже есть в контексте.

Помечается тем же generated_by="llm", что и остальные LLM-провайдеры
порта — по прямому решению пользователя не делать отдельную визуальную
метку "web" в UI (см. dev/QUESTIONS.md).
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request

from app.domain.assistant.chat_responder_port import ChatReply

_COMPLETION_URL = "https://polza.ai/api/v1/chat/completions"
_REQUEST_TIMEOUT_SECONDS = 30
_MAX_TOKENS = 400
_TEMPERATURE = 0.2

_SYSTEM_PROMPT = (
    "Ты — ассистент технолога машиностроительного и аддитивного производства. "
    "Тебе дан вопрос пользователя. В локальной базе нормативно-справочной информации "
    "(НСИ) предприятия ответа не нашлось — используй веб-поиск, чтобы дать полезный "
    "общий ответ на русском языке, кратко (2-5 предложений). Явно укажи в ответе, что "
    "это общая справочная информация из открытых источников, а не данные из локальной "
    "базы НСИ предприятия — не выдавай найденное в интернете за содержимое локальной "
    "базы. Если и в интернете не удалось найти релевантный ответ, честно скажи об этом."
)


class PolzaApiError(RuntimeError):
    pass


class PolzaWebSearchChatResponder:
    def __init__(self, api_key: str, model: str) -> None:
        self._api_key = api_key
        self._model = model

    def reply(self, *, question: str, context_facts: dict) -> ChatReply:
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": question},
            ],
            "temperature": _TEMPERATURE,
            "max_tokens": _MAX_TOKENS,
            "plugins": [{"id": "web"}],
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
            raise PolzaApiError(f"Сетевая ошибка обращения к Polza.ai API (веб-поиск): {exc}") from exc
        except json.JSONDecodeError as exc:
            raise PolzaApiError(f"Некорректный ответ Polza.ai API (веб-поиск): {exc}") from exc

        try:
            text = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as exc:
            raise PolzaApiError(f"Неожиданный формат ответа Polza.ai API (веб-поиск): {body}") from exc

        return ChatReply(text=text.strip(), generated_by="llm")

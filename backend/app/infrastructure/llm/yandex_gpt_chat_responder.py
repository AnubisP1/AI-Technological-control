"""Реализация IChatResponder через облачный YandexGPT API — тот же
паттерн и то же осознанное отступление от офлайн-требования ТЗ, что
YandexGptTextGenerator (см. dev/QUESTIONS.md №12, docs/ARCHITECTURE.md).

Требует сети и ключа API (YANDEX_GPT_API_KEY, YANDEX_GPT_FOLDER_ID в
.env) — при их отсутствии или сетевой ошибке вызывающий код обязан
откатиться на TemplateChatResponder, не падать (см. AssistantService).
Модели запрещено отвечать на основании собственных общих знаний вне
переданного контекста — системный промпт явно требует опираться только
на найденные факты, чтобы не выдавать выдуманные марки/ГОСТы/режимы за
содержимое локальной базы.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request

from app.domain.assistant.chat_responder_port import ChatReply

_COMPLETION_URL = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
_REQUEST_TIMEOUT_SECONDS = 15

_SYSTEM_PROMPT = (
    "Ты — ассистент технолога машиностроительного и аддитивного производства. "
    "Тебе дан вопрос пользователя и список найденных по нему записей из локальной "
    "базы нормативно-справочной информации (НСИ) — материалы, оборудование, оснастка, "
    "операции, режимы резания. Ответь на вопрос на русском языке кратко (2-5 предложений), "
    "используя ТОЛЬКО факты из переданного списка записей — не добавляй маки, ГОСТы, "
    "параметры или рекомендации, которых нет в списке. Если список пуст или не отвечает "
    "на вопрос, честно скажи, что в базе НСИ такой информации не найдено, не выдумывай ответ."
)


class YandexGptApiError(RuntimeError):
    pass


class YandexGptChatResponder:
    def __init__(self, api_key: str, folder_id: str) -> None:
        self._api_key = api_key
        self._folder_id = folder_id

    def reply(self, *, question: str, context_facts: dict) -> ChatReply:
        matches = context_facts.get("matches", [])
        matches_text = "\n".join(f"- {m['table']}: {m['summary']}" for m in matches) or "Записей не найдено."

        payload = {
            "modelUri": f"gpt://{self._folder_id}/yandexgpt-lite",
            "completionOptions": {"stream": False, "temperature": 0.2, "maxTokens": 400},
            "messages": [
                {"role": "system", "text": _SYSTEM_PROMPT},
                {
                    "role": "user",
                    "text": f"Вопрос: {question}\n\nНайденные записи в НСИ:\n{matches_text}",
                },
            ],
        }

        request = urllib.request.Request(
            _COMPLETION_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Api-Key {self._api_key}",
                "x-folder-id": self._folder_id,
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=_REQUEST_TIMEOUT_SECONDS) as response:
                body = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError) as exc:
            raise YandexGptApiError(f"Сетевая ошибка обращения к YandexGPT API: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise YandexGptApiError(f"Некорректный ответ YandexGPT API: {exc}") from exc

        try:
            text = body["result"]["alternatives"][0]["message"]["text"]
        except (KeyError, IndexError) as exc:
            raise YandexGptApiError(f"Неожиданный формат ответа YandexGPT API: {body}") from exc

        return ChatReply(text=text.strip(), generated_by="llm")

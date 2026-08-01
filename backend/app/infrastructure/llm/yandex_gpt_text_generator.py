"""Реализация ITextGenerator через облачный YandexGPT API.

⚠️ ОСОЗНАННОЕ ИСКЛЮЧЕНИЕ ИЗ ОФЛАЙН-ТРЕБОВАНИЯ ТЗ (см. dev/QUESTIONS.md
№12, docs/ARCHITECTURE.md, раздел "Отступление от офлайн-требования").
ТЗ формулирует "Fully offline at runtime. No cloud APIs, no external
LLMs" как Definition-of-Done gate — этот модуль его нарушает по прямому
и явно подтверждённому решению пользователя (Фаза 8), принятому после
того, как ограничение было прямо озвучено и пользователь согласился
пойти на компромисс ради качества текста отчёта.

Требует сети и ключа API (YANDEX_GPT_API_KEY, YANDEX_GPT_FOLDER_ID в
.env) — при их отсутствии или сетевой ошибке вызывающий код обязан
откатиться на TemplateTextGenerator (см. KdReviewService), не падать.
Не используется нигде, кроме одного места (KdReviewService) — это
пилотная интеграция для одного экрана, а не общий механизм.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request

from app.domain.kd_review.text_generator_port import GeneratedText

_COMPLETION_URL = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
_REQUEST_TIMEOUT_SECONDS = 15

_SYSTEM_PROMPT = (
    "Ты — технолог машиностроительного производства. Тебе дан список находок "
    "по результатам сверки чертежа детали со справочником нормативно-справочной "
    "информации (НСИ). Сформулируй связное краткое резюме (3-5 предложений) на "
    "русском языке для главного технолога. Используй ТОЛЬКО факты из списка "
    "находок — не добавляй предположений, которых нет во входных данных, не "
    "придумывай числа или обозначения. Если находок нет, кратко подтверди, что "
    "замечаний по сверке не выявлено."
)


class YandexGptApiError(RuntimeError):
    pass


class YandexGptTextGenerator:
    def __init__(self, api_key: str, folder_id: str) -> None:
        self._api_key = api_key
        self._folder_id = folder_id

    def summarize_review(self, *, facts: dict) -> GeneratedText:
        findings = facts.get("findings", [])
        findings_text = "\n".join(
            f"- [{f['severity']}] {f['message']}" for f in findings
        ) or "Находок нет."

        payload = {
            "modelUri": f"gpt://{self._folder_id}/yandexgpt-lite",
            "completionOptions": {"stream": False, "temperature": 0.2, "maxTokens": 400},
            "messages": [
                {"role": "system", "text": _SYSTEM_PROMPT},
                {"role": "user", "text": f"Находки сверки КД:\n{findings_text}"},
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

        return GeneratedText(text=text.strip(), generated_by="llm")

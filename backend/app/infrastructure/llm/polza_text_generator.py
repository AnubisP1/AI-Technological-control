"""Реализация ITextGenerator через облачный Polza.ai (OpenAI-совместимый
API) — Фаза 18, часть 2 (см. dev/QUESTIONS.md №15).

⚠️ ОСОЗНАННОЕ ИСКЛЮЧЕНИЕ ИЗ ОФЛАЙН-ТРЕБОВАНИЯ ТЗ, ВВЕДЁННОЕ ПОВТОРНО.
Локальный Qwen (QwenTextGenerator, llama-cpp-python) был реализован
именно для того, чтобы вернуться к полному офлайн-соответствию после
того, как облачный YandexGPT (Фаза 8) был осознанным временным
исключением. По прямому решению пользователя Polza.ai работает
ПАРАЛЛЕЛЬНО локальному контуру, не заменяя его: см. _build_text_generator()
в routes.py — облачный путь пробуется первым (ключ уже настроен),
локальный Qwen — фолбэк при отсутствии/ошибке облачного пути, шаблон —
финальный офлайн-фолбэк. Оба реализуют один и тот же промпт
(review_summary_prompt.py), чтобы качество и антигаллюцинационные
ограничения не расходились между провайдерами.

Модель — параметр конструктора, не константа: тариф конкретного ключа
Polza.ai может не давать доступ к произвольной модели из общего каталога
(найдено на практике — qwen/qwen-2.5-7b-instruct отвечал 403 FORBIDDEN,
хотя был в /v1/models). _build_text_generator() в routes.py собирает
несколько инстансов с разными моделями как отдельные звенья цепочки
ChainedTextGenerator, а не один жёстко заданный вызов.

Требует сети и ключа API (POLZA_API_KEY в .env) — при их отсутствии или
сетевой ошибке вызывающий код обязан откатиться на следующий провайдер
в цепочке, не падать (см. KdReviewService._summarize).
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request

from app.domain.kd_review.text_generator_port import GeneratedText
from app.infrastructure.llm.review_summary_prompt import SYSTEM_PROMPT, build_user_prompt

_COMPLETION_URL = "https://polza.ai/api/v1/chat/completions"
_REQUEST_TIMEOUT_SECONDS = 30
_MAX_TOKENS = 500
_TEMPERATURE = 0.2


class PolzaApiError(RuntimeError):
    pass


class PolzaTextGenerator:
    def __init__(self, api_key: str, model: str) -> None:
        self._api_key = api_key
        self._model = model

    def summarize_review(self, *, facts: dict) -> GeneratedText:
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_user_prompt(facts)},
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

        return GeneratedText(text=text.strip(), generated_by="llm")

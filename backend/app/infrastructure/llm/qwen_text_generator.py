"""Реализация ITextGenerator через локальный Qwen2.5-7B-Instruct (GGUF,
llama-cpp-python) — Фаза 18, заменяет прежний облачный YandexGptTextGenerator
(см. dev/QUESTIONS.md №14). Полностью офлайн: вес модели скачивается один
раз при установке (dev/README.md), инференс не требует сети в рантайме.

Единственный LLM-провайдер локальной (offline) сборки: облачные
адаптеры из этого контура исключены. Промпт вынесен в
review_summary_prompt.py, сборка провайдера — _build_text_generator()
в routes.py; при отсутствии файла модели используется шаблонный текст.

Промпт передаёт модели не только уже готовые findings, но и ПОЛНЫЙ список
материалов НСИ с их технологическими свойствами (плотность/прочность/
твёрдость/индекс обрабатываемости) — по прямому запросу пользователя,
чтобы получить реальную аналитику технологичности и предложение аналога,
а не просто более связную прозу поверх уже принятого кодом решения. Само
решение (какой материал "подходит") по-прежнему принимает
детерминированный код (match_material) — LLM анализирует и поясняет, не
подменяет его.

Выполняется через run_heavy() (ProcessPoolExecutor, max_workers=1) —
чистая CPU-нагрузка нескольких секунд не должна блокировать event loop
FastAPI (см. worker_pool.py, resource_governor.py).
"""

from __future__ import annotations

from pathlib import Path

from app.domain.kd_review.text_generator_port import GeneratedText
from app.infrastructure.llm.llama_cpp_engine import get_engine
from app.infrastructure.llm.review_summary_prompt import SYSTEM_PROMPT, build_user_prompt

_MAX_TOKENS = 500
_TEMPERATURE = 0.2


class QwenTextGenerator:
    def __init__(self, model_path: Path, context_size: int) -> None:
        self._model_path = model_path
        self._context_size = context_size

    def summarize_review(self, *, facts: dict) -> GeneratedText:
        engine = get_engine(self._model_path, self._context_size)
        text = engine.complete(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=build_user_prompt(facts),
            max_tokens=_MAX_TOKENS,
            temperature=_TEMPERATURE,
        )
        return GeneratedText(text=text, generated_by="llm")

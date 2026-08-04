"""Модульный ленивый синглтон загрузки локальной GGUF-модели через
llama-cpp-python (Фаза 18) — CPU-only, полностью офлайн после установки.

Почему модульный синглтон, а не singleton-класс с DI: этот движок
вызывается только из тяжёлых задач, выполняемых через run_heavy()
(app/infrastructure/worker_pool.py), который использует
ProcessPoolExecutor с max_workers=1 — то есть все вызовы фактически
попадают в один и тот же worker-процесс. Loading модели занимает
секунды, а инференс должен переиспользовать уже загруженные веса между
запросами (иначе каждый запрос платит полную загрузку 7B-модели) — тот
же module-level кэш внутри воркер-процесса решает это без передачи
объекта Llama через pickle (что и не сработало бы — llama_cpp.Llama не
предназначен для передачи между процессами).

Число потоков берётся из общего resource governor (см.
resource_governor.py) — тот же CPU-бюджет floor(0.4 * cpu_count), что и
для остальных вычислительных движков проекта.
"""

from __future__ import annotations

from pathlib import Path

from app.infrastructure.resource_governor import configure as get_resource_limits

_engine: "_LlamaCppEngine | None" = None


class LlamaModelUnavailableError(RuntimeError):
    pass


class _LlamaCppEngine:
    def __init__(self, model_path: Path, context_size: int) -> None:
        from llama_cpp import Llama

        limits = get_resource_limits()
        self._llama = Llama(
            model_path=str(model_path),
            n_ctx=context_size,
            n_threads=limits.thread_count,
            verbose=False,
        )

    def complete(self, *, system_prompt: str, user_prompt: str, max_tokens: int, temperature: float) -> str:
        result = self._llama.create_chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return result["choices"][0]["message"]["content"].strip()


def get_engine(model_path: Path, context_size: int) -> _LlamaCppEngine:
    """Возвращает загруженный движок, создавая его при первом обращении
    в текущем процессе. Не потокобезопасно намеренно — единственный
    вызывающий (run_heavy) сериализует задачи через max_workers=1."""
    global _engine
    if _engine is None:
        if not model_path.exists():
            raise LlamaModelUnavailableError(
                f"Файл модели не найден: {model_path} — см. dev/README.md, "
                "раздел установки Qwen."
            )
        _engine = _LlamaCppEngine(model_path, context_size)
    return _engine

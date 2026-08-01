"""Пул-воркер с ограниченным параллелизмом для тяжёлых задач (STEP-парсинг,
инференс), чтобы не блокировать event loop FastAPI и не дать нескольким
моделям одновременно конкурировать за CPU (требование ТЗ: инференс
батчами/последовательно).

Размер пула — не число потоков ONNX/torch (это отдельный лимит в
resource_governor), а число одновременно выполняемых тяжёлых задач.
По умолчанию 1: тяжёлые задачи выполняются строго последовательно, что
проще всего удерживает суммарную загрузку CPU в рамках бюджета, когда
каждая задача уже сама использует governor-ограниченное число потоков.
"""

from __future__ import annotations

import asyncio
from concurrent.futures import ProcessPoolExecutor
from typing import Callable, TypeVar

T = TypeVar("T")

_executor: ProcessPoolExecutor | None = None


def get_executor(max_workers: int = 1) -> ProcessPoolExecutor:
    global _executor
    if _executor is None:
        _executor = ProcessPoolExecutor(max_workers=max_workers)
    return _executor


async def run_heavy(func: Callable[..., T], *args, **kwargs) -> T:
    """Выполняет тяжёлую синхронную функцию в воркер-пуле, не блокируя event loop."""
    loop = asyncio.get_running_loop()
    executor = get_executor()
    if kwargs:
        return await loop.run_in_executor(executor, lambda: func(*args, **kwargs))
    return await loop.run_in_executor(executor, func, *args)


def shutdown() -> None:
    global _executor
    if _executor is not None:
        _executor.shutdown(wait=True)
        _executor = None

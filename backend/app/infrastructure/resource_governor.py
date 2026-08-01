"""Центральный ресурс-губернатор: единая точка настройки числа потоков
для всех вычислительных движков (ГОСТ CPU-бюджет из ТЗ: не более 40-60% CPU).

Требование ТЗ: единообразно управлять OMP_NUM_THREADS, torch.set_num_threads,
ONNX Runtime intra_op/inter_op_num_threads, по умолчанию floor(0.4 * cpu_count).
Вызывать configure() один раз при старте процесса, до импорта/использования
любых ML-библиотек (torch, onnxruntime), т.к. многие читают переменные
окружения на этапе импорта.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

DEFAULT_CPU_FRACTION = 0.4


@dataclass(frozen=True)
class ResourceLimits:
    thread_count: int
    cpu_fraction: float
    cpu_count_total: int


def _detect_cpu_count() -> int:
    count = os.cpu_count()
    return count if count else 1


def _thread_count_from_fraction(cpu_fraction: float, cpu_count_total: int) -> int:
    return max(1, int(cpu_count_total * cpu_fraction))


@lru_cache(maxsize=1)
def configure(cpu_fraction: float | None = None) -> ResourceLimits:
    """Настраивает лимиты потоков для всех известных ML/численных движков.

    Идемпотентна в рамках процесса (lru_cache) — повторный вызов с другим
    аргументом в течение жизни процесса не переустановит уже примененные
    переменные окружения для движков, читающих их при импорте.
    """
    fraction = cpu_fraction if cpu_fraction is not None else float(
        os.environ.get("CPU_BUDGET_FRACTION", DEFAULT_CPU_FRACTION)
    )
    cpu_count_total = _detect_cpu_count()
    thread_count = _thread_count_from_fraction(fraction, cpu_count_total)

    os.environ["OMP_NUM_THREADS"] = str(thread_count)
    os.environ["MKL_NUM_THREADS"] = str(thread_count)
    os.environ["OPENBLAS_NUM_THREADS"] = str(thread_count)

    try:
        import torch

        torch.set_num_threads(thread_count)
    except ImportError:
        pass

    return ResourceLimits(
        thread_count=thread_count,
        cpu_fraction=fraction,
        cpu_count_total=cpu_count_total,
    )


def onnxruntime_session_options(limits: ResourceLimits | None = None):
    """Возвращает ort.SessionOptions с примененным лимитом потоков.

    Импортирует onnxruntime лениво — вызывающий код решает, когда она нужна,
    чтобы не тянуть тяжёлую зависимость туда, где инференс не используется.
    """
    import onnxruntime as ort

    limits = limits or configure()
    options = ort.SessionOptions()
    options.intra_op_num_threads = limits.thread_count
    options.inter_op_num_threads = limits.thread_count
    return options

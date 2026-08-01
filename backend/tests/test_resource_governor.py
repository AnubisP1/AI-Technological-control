import os

from app.infrastructure.resource_governor import _thread_count_from_fraction, configure


def test_thread_count_is_floor_of_fraction_times_cpu_count():
    assert _thread_count_from_fraction(0.4, 10) == 4
    assert _thread_count_from_fraction(0.4, 3) == 1  # минимум 1 поток


def test_configure_sets_omp_num_threads_env_var():
    # configure() кэширован (lru_cache) — в рамках процесса он идемпотентен,
    # поэтому проверяем консистентность уже применённых лимитов, а не
    # конкретное значение fraction (порядок тестов в сессии не гарантирован).
    limits = configure()
    assert os.environ["OMP_NUM_THREADS"] == str(limits.thread_count)
    assert limits.thread_count == max(1, int(limits.cpu_count_total * limits.cpu_fraction))

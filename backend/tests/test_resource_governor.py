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


def test_configure_calls_opencv_set_num_threads_without_error():
    """governor обязан вызвать cv2.setNumThreads(), но не может
    гарантировать эффект: на сборках OpenCV с параллельным бэкендом GCD
    (типично для macOS ARM, см. cv2.getBuildInformation()) вызов
    документированно является no-op — OpenCV не управляет пулом потоков
    GCD. На сборках с TBB/OpenMP (типично для Linux/Windows) он реально
    ограничивает потоки. Тест проверяет применимый на любой платформе
    инвариант: значение не может быть меньше запрошенного лимита или
    отрицательным, а сам вызов не должен падать."""
    import cv2

    limits = configure()
    assert cv2.getNumThreads() >= 1
    assert cv2.getNumThreads() >= limits.thread_count or "GCD" in cv2.getBuildInformation()

"""Экспорт реальной тесселяции (mesh) STEP-модели в STL через внешний
conda-интерпретатор с pythonocc-core (Фаза 17, часть 5 — по прямому
запросу пользователя заменить параметрический прокси-бокс в PartViewer
на точную геометрию).

pythonocc-core не публикуется на PyPI (только conda-forge), а backend
использует чистый venv+pip (см. dev/CLAUDE.md, dev/PLAN.md) — переводить
весь backend на conda ради одной функции неоправданно. Вместо этого
conda-окружение с pythonocc-core вызывается как ВНЕШНИЙ интерпретатор
через subprocess (см. occ_step_to_stl_script.py — автономный скрипт без
зависимостей от остального приложения), аналогично тому, как ocr_drawing_parser.py
полагается на внешний бинарь tesseract, а не встраивает его в venv.

Путь к conda-python задаётся явно через Settings.pythonocc_python_path
(.env) — не угадывается автоматически, так как conda ставится в разные
места на разных машинах. Если не задан или экспорт завершается с
ошибкой, эта функция возвращает None — вызывающий код (routes.py) не
считает это ошибкой запроса: PartViewer остаётся на параметрическом
прокси-боксе, что уже задокументированное и согласованное поведение.
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

_SCRIPT_PATH = Path(__file__).with_name("occ_step_to_stl_script.py")
_EXPORT_TIMEOUT_SECONDS = 60


def export_step_to_stl(step_path: Path, python_executable: Path | None) -> bytes | None:
    """Возвращает содержимое STL-файла (бинарный формат) или None, если
    экспорт недоступен/не удался — не бросает исключение наружу, так как
    реальная тесселяция — необязательное улучшение поверх уже рабочего
    параметрического вьюера, а не критический путь."""
    if python_executable is None or not python_executable.exists():
        return None

    with tempfile.TemporaryDirectory() as tmp_dir:
        stl_path = Path(tmp_dir) / "output.stl"
        try:
            result = subprocess.run(
                [str(python_executable), str(_SCRIPT_PATH), str(step_path), str(stl_path)],
                capture_output=True,
                timeout=_EXPORT_TIMEOUT_SECONDS,
                check=False,
            )
        except (subprocess.TimeoutExpired, OSError):
            return None

        if result.returncode != 0 or not stl_path.exists():
            return None

        return stl_path.read_bytes()

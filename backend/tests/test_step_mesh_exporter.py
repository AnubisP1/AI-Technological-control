from pathlib import Path

import pytest

from app.infrastructure.cad.step_mesh_exporter import export_step_to_stl
from app.infrastructure.config import get_settings

FIXTURES_ROOT = Path(__file__).resolve().parents[3] / "КД для тестов"
VAL_STEP = FIXTURES_ROOT / "Детали из металла" / "1. Тестовая деталь металл" / "3D_К200-150-400 - Вал.stp"


def _require(path: Path) -> Path:
    if not path.exists():
        pytest.skip(f"fixture недоступен в этом окружении: {path}")
    return path


def _require_pythonocc() -> Path:
    python_path = get_settings().pythonocc_python_path
    if python_path is None or not python_path.exists():
        pytest.skip("PYTHONOCC_PYTHON_PATH не настроен в этом окружении — реальная тесселяция недоступна")
    return python_path


def test_export_step_to_stl_produces_valid_binary_stl_for_real_fixture():
    """Реальный fixture (вал) — конкретное число треугольников не
    проверяется (зависит от параметров мешинга внутри OCC, не публичная
    величина), но бинарный STL должен иметь корректный заголовок формата
    (80-байтовый header + uint32 число треугольников) и ненулевой размер."""
    python_path = _require_pythonocc()
    step_path = _require(VAL_STEP)

    stl_bytes = export_step_to_stl(step_path, python_path)

    assert stl_bytes is not None
    assert len(stl_bytes) > 84  # 80-байтовый заголовок + 4-байтовый счётчик треугольников
    triangle_count = int.from_bytes(stl_bytes[80:84], byteorder="little")
    assert triangle_count > 0
    # Бинарный STL: заголовок (80) + счётчик (4) + N * 50 байт на треугольник.
    assert len(stl_bytes) == 84 + triangle_count * 50


def test_export_step_to_stl_returns_none_when_python_path_missing():
    step_path = _require(VAL_STEP)
    assert export_step_to_stl(step_path, None) is None


def test_export_step_to_stl_returns_none_when_python_path_does_not_exist():
    step_path = _require(VAL_STEP)
    assert export_step_to_stl(step_path, Path("/nonexistent/python")) is None

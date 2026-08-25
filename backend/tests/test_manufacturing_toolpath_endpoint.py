from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.infrastructure.config import get_settings
from app.main import app

METAL_FIXTURES_ROOT = Path(__file__).resolve().parents[3] / "КД для тестов" / "Детали из металла"
VAL_PDF = METAL_FIXTURES_ROOT / "1. Тестовая деталь металл" / "К200-150-400ENERAL.20 - Вал.pdf"
VAL_STEP = METAL_FIXTURES_ROOT / "1. Тестовая деталь металл" / "3D_К200-150-400 - Вал.stp"

LITERATURE_ROOT = Path(__file__).resolve().parents[3] / "Литература" / "НПО 2026"
BRACKET_STEP = LITERATURE_ROOT / "Кронштейн" / "Кронштейн.STEP"

client = TestClient(app)


def _require(path: Path) -> Path:
    if not path.exists():
        pytest.skip(f"fixture недоступен в этом окружении: {path}")
    return path


def _require_pythonocc():
    settings = get_settings()
    if settings.pythonocc_python_path is None or not settings.pythonocc_python_path.exists():
        pytest.skip("PYTHONOCC_PYTHON_PATH не настроен в этом окружении")


def _post_toolpath(step_path: Path, drawing_path: Path):
    with step_path.open("rb") as step_file, drawing_path.open("rb") as drawing_file:
        return client.post(
            "/manufacturing/toolpath/metal",
            files={
                "step_model": (step_path.name, step_file, "application/octet-stream"),
                "drawing": (drawing_path.name, drawing_file, "application/pdf"),
            },
        )


def test_toolpath_endpoint_returns_real_operations_for_supported_bracket_geometry():
    """Кронштейн.STEP (призматическая деталь, реальная топология) в паре
    с чертежом вала (даёт material_grade стали — деталь и чертёж физически
    не одна и та же, но эндпоинт логически не требует совпадения: STEP
    даёт геометрию, чертёж даёт марку материала) — проверяет полный
    сквозной путь через реальный HTTP-запрос."""
    _require_pythonocc()
    step_path = _require(BRACKET_STEP)
    drawing_path = _require(VAL_PDF)

    response = _post_toolpath(step_path, drawing_path)

    assert response.status_code == 200
    body = response.json()
    toolpath = body["toolpath"]

    assert toolpath["unsupported_warning"] is None
    assert len(toolpath["operations"]) >= 2
    for op in toolpath["operations"]:
        assert op["spindle_speed_rpm"] > 0
        assert op["feed_mm_min"] > 0
        assert len(op["gcode_lines"]) > 0
        assert op["source_note"]
        # Координаты движения инструмента — нужны фронтенду для анимации
        # положения фрезы (ToolpathViewer.tsx), не только текстовый G-code.
        assert len(op["moves"]) > 0
        for move in op["moves"]:
            assert move["kind"] in ("rapid", "linear", "arc_cw", "arc_ccw")
            assert isinstance(move["x_mm"], (int, float))

    simulation = body["simulation"]
    assert simulation is not None
    assert simulation["total_steps"] > 0
    assert len(simulation["events"]) > 0
    # Компактный формат [x, y, z, шаг] — 4 элемента на событие.
    assert len(simulation["events"][0]) == 4


def test_toolpath_endpoint_returns_unsupported_warning_for_shaft_revolved_body():
    """Вал (тело вращения — точение, не наш v1) с его собственным
    настоящим чертежом — обязан вернуть честное предупреждение, не
    операции по несуществующей "фрезерной" стратегии для этой геометрии."""
    _require_pythonocc()
    step_path = _require(VAL_STEP)
    drawing_path = _require(VAL_PDF)

    response = _post_toolpath(step_path, drawing_path)

    assert response.status_code == 200
    body = response.json()
    toolpath = body["toolpath"]

    assert toolpath["unsupported_warning"] is not None
    assert toolpath["operations"] == []
    assert body["simulation"] is None

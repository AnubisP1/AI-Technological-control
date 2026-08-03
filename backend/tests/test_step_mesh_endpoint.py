from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.infrastructure.config import get_settings
from app.main import app

FIXTURES_ROOT = Path(__file__).resolve().parents[3] / "КД для тестов"
VAL_STEP = FIXTURES_ROOT / "Детали из металла" / "1. Тестовая деталь металл" / "3D_К200-150-400 - Вал.stp"

client = TestClient(app)


def _require(path: Path) -> Path:
    if not path.exists():
        pytest.skip(f"fixture недоступен в этом окружении: {path}")
    return path


def _require_pythonocc() -> None:
    python_path = get_settings().pythonocc_python_path
    if python_path is None or not python_path.exists():
        pytest.skip("PYTHONOCC_PYTHON_PATH не настроен в этом окружении — реальная тесселяция недоступна")


def test_step_mesh_endpoint_returns_binary_stl_for_real_fixture():
    _require_pythonocc()
    step_path = _require(VAL_STEP)

    with step_path.open("rb") as step_file:
        response = client.post(
            "/kd/step-mesh", files={"step_model": (step_path.name, step_file, "application/octet-stream")}
        )

    assert response.status_code == 200
    assert response.headers["content-type"] == "model/stl"
    assert len(response.content) > 84

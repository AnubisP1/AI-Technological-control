"""Извлечение топологии STEP-модели (грани по типу поверхности) через
внешний conda-интерпретатор с pythonocc-core (Фаза 22 — реальный
CAM-тулпас, dev/PLAN.md).

Тот же паттерн, что и step_mesh_exporter.py: pythonocc-core не
публикуется на PyPI (только conda-forge), поэтому вызывается как ВНЕШНИЙ
интерпретатор через subprocess (occ_feature_extract_script.py — автономный
скрипт без зависимостей от остального приложения), а не встраивается в
основной venv.

В отличие от step_mesh_exporter (недоступность = тихий откат на
параметрический прокси-бокс, не критический путь), здесь недоступность
pythonocc возвращается вызывающему коду как None и ДОЛЖНА привести к
честному "автогенерация тулпаса недоступна" — генерация G-code без
реальной топологии была бы фабрикацией траектории, что запрещено
проектной дисциплиной (см. CLAUDE.md "Никогда не выдумывать НСИ-данные").
"""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

from app.domain.cad.feature_model import CylindricalFace, PartTopology, PlanarFace

_SCRIPT_PATH = Path(__file__).with_name("occ_feature_extract_script.py")
_EXTRACT_TIMEOUT_SECONDS = 60


def extract_step_topology(step_path: Path, python_executable: Path | None) -> PartTopology | None:
    """Возвращает распознанную топологию граней или None, если pythonocc
    недоступен/извлечение не удалось — вызывающий код (ToolpathGeneratorService
    через сервис планирования) обязан трактовать None как "автогенерация
    тулпаса невозможна для этой детали", не как "деталь без фич"."""
    if python_executable is None or not python_executable.exists():
        return None

    with tempfile.TemporaryDirectory() as tmp_dir:
        json_path = Path(tmp_dir) / "features.json"
        try:
            result = subprocess.run(
                [str(python_executable), str(_SCRIPT_PATH), str(step_path), str(json_path)],
                capture_output=True,
                timeout=_EXTRACT_TIMEOUT_SECONDS,
                check=False,
            )
        except (subprocess.TimeoutExpired, OSError):
            return None

        if result.returncode != 0 or not json_path.exists():
            return None

        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

    return _parse_topology(data)


def _parse_topology(data: dict) -> PartTopology:
    planar_faces = tuple(
        PlanarFace(
            origin_mm=(f["origin"][0], f["origin"][1], f["origin"][2]),
            normal=(f["normal"][0], f["normal"][1], f["normal"][2]),
            extent_u_mm=f["extent_u"],
            extent_v_mm=f["extent_v"],
        )
        for f in data.get("planar_faces", [])
    )
    cylindrical_faces = tuple(
        CylindricalFace(
            radius_mm=f["radius_mm"],
            axis_origin_mm=(f["axis_origin"][0], f["axis_origin"][1], f["axis_origin"][2]),
            axis_direction=(f["axis_direction"][0], f["axis_direction"][1], f["axis_direction"][2]),
            angular_extent_rad=f["angular_extent_rad"],
            is_full_turn=f["is_full_turn"],
            height_mm=f["height_mm"],
        )
        for f in data.get("cylindrical_faces", [])
    )
    bb = data["bounding_box"]
    return PartTopology(
        planar_faces=planar_faces,
        cylindrical_faces=cylindrical_faces,
        other_face_count=data.get("other_face_count", 0),
        total_face_count=data.get("total_face_count", 0),
        bounding_box_mm=(bb["x_min"], bb["x_max"], bb["y_min"], bb["y_max"], bb["z_min"], bb["z_max"]),
    )

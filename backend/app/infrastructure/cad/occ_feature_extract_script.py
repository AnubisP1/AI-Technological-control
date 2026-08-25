"""Автономный скрипт извлечения топологии STEP через pythonocc-core (OpenCASCADE).

Тот же принцип subprocess-границы, что и occ_step_to_stl_script.py (см.
docstring этого файла) — запускается отдельным процессом внутри
conda-окружения с pythonocc-core, не импортируется напрямую из основного
backend-процесса. Файл намеренно не зависит от остального кода
приложения (нет импортов из app.*).

В отличие от occ_step_to_stl_script.py (тесселяция в mesh для рендера),
этот скрипт обходит B-rep напрямую и классифицирует каждую грань по типу
геометрии (плоскость/цилиндр/другое) — основа для распознавания
обрабатываемых фич (Фаза 22, dev/PLAN.md).

Критерий "сквозное отверстие vs галтель-скругление" для цилиндрических
граней — угловой охват параметра U (полный оборот 2π ~= отверстие,
заметно меньше ~= скругление кромки, обычно ~=π/2 для скругления прямого
угла) — эмпирически подтверждён на реальном fixture (Кронштейн.STEP,
20 граней: 1 сквозное отверстие Ø25 с полным углом 2π против 4 галтелей
R10 с углом ~=π/2 каждая), не выдуманное правило.
"""

from __future__ import annotations

import json
import math
import sys

_FULL_TURN_TOLERANCE_RAD = 0.35  # ~20° — насколько меньше 2π ещё считается "полным" отверстием
_TWO_PI = 2 * math.pi


def _classify_faces(shape) -> dict:
    from OCC.Core.BRepAdaptor import BRepAdaptor_Surface
    from OCC.Core.GeomAbs import GeomAbs_Cylinder, GeomAbs_Plane
    from OCC.Core.TopAbs import TopAbs_FACE
    from OCC.Core.TopExp import TopExp_Explorer
    from OCC.Core.TopoDS import topods

    planar_faces: list[dict] = []
    cylindrical_faces: list[dict] = []
    other_face_count = 0

    explorer = TopExp_Explorer(shape, TopAbs_FACE)
    while explorer.More():
        face = topods.Face(explorer.Current())
        surface = BRepAdaptor_Surface(face, True)
        surface_type = surface.GetType()

        if surface_type == GeomAbs_Plane:
            plane = surface.Plane()
            location = plane.Location()
            normal = plane.Axis().Direction()
            u1, u2 = surface.FirstUParameter(), surface.LastUParameter()
            v1, v2 = surface.FirstVParameter(), surface.LastVParameter()
            planar_faces.append(
                {
                    "origin": [location.X(), location.Y(), location.Z()],
                    "normal": [normal.X(), normal.Y(), normal.Z()],
                    "extent_u": abs(u2 - u1),
                    "extent_v": abs(v2 - v1),
                }
            )
        elif surface_type == GeomAbs_Cylinder:
            cylinder = surface.Cylinder()
            axis = cylinder.Axis()
            location = axis.Location()
            direction = axis.Direction()
            u1, u2 = surface.FirstUParameter(), surface.LastUParameter()
            v1, v2 = surface.FirstVParameter(), surface.LastVParameter()
            angular_extent = abs(u2 - u1)
            cylindrical_faces.append(
                {
                    "radius_mm": cylinder.Radius(),
                    "axis_origin": [location.X(), location.Y(), location.Z()],
                    "axis_direction": [direction.X(), direction.Y(), direction.Z()],
                    "angular_extent_rad": angular_extent,
                    "is_full_turn": angular_extent >= (_TWO_PI - _FULL_TURN_TOLERANCE_RAD),
                    "height_mm": abs(v2 - v1),
                }
            )
        else:
            other_face_count += 1

        explorer.Next()

    return {
        "planar_faces": planar_faces,
        "cylindrical_faces": cylindrical_faces,
        "other_face_count": other_face_count,
        "total_face_count": len(planar_faces) + len(cylindrical_faces) + other_face_count,
    }


def _bounding_box(shape) -> dict:
    from OCC.Core.Bnd import Bnd_Box
    from OCC.Core.BRepBndLib import brepbndlib

    box = Bnd_Box()
    brepbndlib.Add(shape, box)
    x_min, y_min, z_min, x_max, y_max, z_max = box.Get()
    return {
        "x_min": x_min, "x_max": x_max,
        "y_min": y_min, "y_max": y_max,
        "z_min": z_min, "z_max": z_max,
    }


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: occ_feature_extract_script.py <step_path> <json_path>", file=sys.stderr)
        return 2

    step_path, json_path = sys.argv[1], sys.argv[2]

    from OCC.Core.IFSelect import IFSelect_RetDone
    from OCC.Core.STEPControl import STEPControl_Reader

    reader = STEPControl_Reader()
    status = reader.ReadFile(step_path)
    if status != IFSelect_RetDone:
        print(f"STEP read failed with status {status}", file=sys.stderr)
        return 1

    # TransferRoot(1)+Shape(1) — тот же выбор, что в occ_step_to_stl_script.py
    # (см. его docstring: TransferRoots()+OneShape() молча даёт 0 корней
    # на части реальных тестовых STEP-файлов проекта).
    if reader.NbRootsForTransfer() < 1 or not reader.TransferRoot(1):
        print("no transferable roots in STEP file", file=sys.stderr)
        return 1
    shape = reader.Shape(1)
    if shape is None or shape.IsNull():
        print("STEP file produced an empty/null shape", file=sys.stderr)
        return 1

    result = {
        "bounding_box": _bounding_box(shape),
        **_classify_faces(shape),
    }

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result, f)

    return 0


if __name__ == "__main__":
    sys.exit(main())

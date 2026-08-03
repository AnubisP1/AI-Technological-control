"""Автономный скрипт экспорта STEP -> STL через pythonocc-core (OpenCASCADE).

ВАЖНО: этот файл запускается отдельным процессом внутри conda-окружения
с pythonocc-core (см. app/infrastructure/cad/step_mesh_exporter.py), НЕ
импортируется напрямую из основного backend-процесса — основной venv
не имеет доступа к OCC (pythonocc-core не публикуется на PyPI). Файл
намеренно не зависит от остального кода приложения (нет импортов из
app.*), чтобы его можно было запустить `python occ_step_to_stl_script.py
<step_path> <stl_path>` в изолированном интерпретаторе без sys.path
эквилибристики.

Линейное отклонение мешинга (0.3мм) — компромисс между точностью
поверхности и размером/временем генерации STL для деталей масштаба
БПЛА-компонентов (десятки-сотни мм), не публичная научная величина —
подобрано эмпирически на реальных тестовых fixture проекта.
"""

from __future__ import annotations

import sys

_MESH_LINEAR_DEFLECTION_MM = 0.3


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: occ_step_to_stl_script.py <step_path> <stl_path>", file=sys.stderr)
        return 2

    step_path, stl_path = sys.argv[1], sys.argv[2]

    from OCC.Core.BRepMesh import BRepMesh_IncrementalMesh
    from OCC.Core.IFSelect import IFSelect_RetDone
    from OCC.Core.StlAPI import StlAPI_Writer
    from OCC.Core.STEPControl import STEPControl_Reader

    reader = STEPControl_Reader()
    status = reader.ReadFile(step_path)
    if status != IFSelect_RetDone:
        print(f"STEP read failed with status {status}", file=sys.stderr)
        return 1

    # TransferRoot(1) + Shape(1), а не TransferRoots()+OneShape() — второй
    # вариант молча даёт 0 переданных корней (и, соответственно, None
    # вместо формы) на части реальных тестовых STEP-файлов проекта
    # (напр. сложные многоуровневые сборки), хотя ReadFile() отчитывается
    # об успехе. Первый вариант надёжно работает и на простых деталях, и
    # на этих сборках — найдено эмпирически на реальных fixture проекта.
    if reader.NbRootsForTransfer() < 1 or not reader.TransferRoot(1):
        print("no transferable roots in STEP file", file=sys.stderr)
        return 1
    shape = reader.Shape(1)
    if shape is None or shape.IsNull():
        print("STEP file produced an empty/null shape", file=sys.stderr)
        return 1

    mesh = BRepMesh_IncrementalMesh(shape, _MESH_LINEAR_DEFLECTION_MM)
    mesh.Perform()
    if not mesh.IsDone():
        print("mesh generation did not complete", file=sys.stderr)
        return 1

    writer = StlAPI_Writer()
    writer.SetASCIIMode(False)
    if not writer.Write(shape, stl_path):
        print("STL write failed", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

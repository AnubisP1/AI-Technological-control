"""Voxel-симуляция реального съёма материала по вычисленному тулпасу
(Фаза 22, dev/PLAN.md) — по прямому запросу пользователя: "давай делать
полноценный инструмент с визуализацией прохода фрезы по заготовке до
получения вида электронной модели (в ускоренном темпе...)".

Заготовка представляется воксельной сеткой (numpy bool-массив), изначально
полностью заполненной материалом. Каждое движение инструмента (ToolpathMove)
из уже вычисленного ToolpathPlan (реальные координаты, не декоративная
анимация) "вырезает" воксели в радиусе tool_diameter_mm/2 вдоль отрезка
движения — детерминированная растеризация, не boolean CSG (оправданно
разрешением сетки, см. _MAX_VOXELS_PER_AXIS).

Результат — не полный покадровый вывод (при десятках тысяч вокселей и
сотнях движений это было бы огромным объёмом данных), а компактный
sparse-список событий "воксель удалён на шаге N" — тот же принцип
постепенного раскрытия, что уже применяется для program_lines (typewriter
reveal), только для 3D: фронтенд сам восстанавливает прогрессию по
порогу шага.

CPU-тяжёлая numpy-операция — вызывается через run_heavy (ProcessPoolExecutor,
governor уже ограничивает число потоков BLAS/OMP на уровне процесса, см.
app/infrastructure/resource_governor.py).
"""

from __future__ import annotations

import math

import numpy as np

from app.domain.manufacturing.toolpath_model import (
    MaterialRemovalSimulation,
    ToolpathPlan,
    VoxelGridSpec,
    VoxelRemovalEvent,
)

_MAX_VOXELS_PER_AXIS = 120  # бюджет разрешения сетки — компромисс точности/производительности на CPU-бюджете проекта
_MIN_VOXEL_SIZE_MM = 0.5


def simulate_material_removal(plan: ToolpathPlan) -> MaterialRemovalSimulation:
    x_min, x_max, y_min, y_max, z_min, z_max = plan.stock_bounding_box_mm
    span_x, span_y, span_z = x_max - x_min, y_max - y_min, z_max - z_min
    max_span = max(span_x, span_y, span_z, 1e-6)

    voxel_size_mm = max(_MIN_VOXEL_SIZE_MM, max_span / _MAX_VOXELS_PER_AXIS)

    nx = max(1, math.ceil(span_x / voxel_size_mm))
    ny = max(1, math.ceil(span_y / voxel_size_mm))
    nz = max(1, math.ceil(span_z / voxel_size_mm))

    grid = VoxelGridSpec(origin_mm=(x_min, y_min, z_min), voxel_size_mm=voxel_size_mm, dims=(nx, ny, nz))

    material = np.ones((nx, ny, nz), dtype=bool)
    events: list[VoxelRemovalEvent] = []
    step = 0

    for operation in plan.operations:
        radius_mm = operation.tool_diameter_mm / 2
        for prev_move, curr_move in zip(operation.moves, operation.moves[1:]):
            if curr_move.kind == "rapid":
                # Быстрые холостые ходы не режут материал.
                continue
            step += 1
            _carve_segment(
                material=material,
                grid=grid,
                start_mm=(prev_move.x_mm, prev_move.y_mm, prev_move.z_mm),
                end_mm=(curr_move.x_mm, curr_move.y_mm, curr_move.z_mm),
                radius_mm=radius_mm,
                step=step,
                events=events,
            )

    return MaterialRemovalSimulation(grid=grid, events=tuple(events), total_steps=step)


def _carve_segment(
    *,
    material: np.ndarray,
    grid: VoxelGridSpec,
    start_mm: tuple[float, float, float],
    end_mm: tuple[float, float, float],
    radius_mm: float,
    step: int,
    events: list[VoxelRemovalEvent],
) -> None:
    ox, oy, oz = grid.origin_mm
    voxel_size = grid.voxel_size_mm
    nx, ny, nz = grid.dims

    seg_length_mm = math.dist(start_mm, end_mm)
    # Точки вдоль отрезка с шагом не более половины вокселя, чтобы не
    # оставлять "дыр" растеризации между соседними точками выборки.
    sample_count = max(1, math.ceil(seg_length_mm / (voxel_size / 2)))

    radius_in_voxels = max(1, math.ceil(radius_mm / voxel_size))

    for i in range(sample_count + 1):
        t = i / sample_count if sample_count > 0 else 0.0
        px = start_mm[0] + (end_mm[0] - start_mm[0]) * t
        py = start_mm[1] + (end_mm[1] - start_mm[1]) * t
        pz = start_mm[2] + (end_mm[2] - start_mm[2]) * t

        cvx = int((px - ox) / voxel_size)
        cvy = int((py - oy) / voxel_size)
        cvz = int((pz - oz) / voxel_size)

        x_lo, x_hi = max(0, cvx - radius_in_voxels), min(nx, cvx + radius_in_voxels + 1)
        y_lo, y_hi = max(0, cvy - radius_in_voxels), min(ny, cvy + radius_in_voxels + 1)
        z_lo, z_hi = max(0, cvz - radius_in_voxels), min(nz, cvz + radius_in_voxels + 1)
        if x_lo >= x_hi or y_lo >= y_hi or z_lo >= z_hi:
            continue

        # Инструмент — цилиндр (фреза/сверло): вырезает по радиусу в
        # плоскости XY, ограничение по Z не применяется здесь отдельно
        # (глубина реза уже задана координатами самой траектории).
        xs, ys = np.meshgrid(
            np.arange(x_lo, x_hi) - cvx, np.arange(y_lo, y_hi) - cvy, indexing="ij"
        )
        within_radius = (xs**2 + ys**2) <= radius_in_voxels**2

        region = material[x_lo:x_hi, y_lo:y_hi, z_lo:z_hi]
        for zi in range(region.shape[2]):
            slice_mask = within_radius & region[:, :, zi]
            if not slice_mask.any():
                continue
            removed_local = np.argwhere(slice_mask)
            for lx, ly in removed_local:
                region[lx, ly, zi] = False
                events.append(
                    VoxelRemovalEvent(
                        voxel_x=int(x_lo + lx), voxel_y=int(y_lo + ly), voxel_z=int(z_lo + zi), removed_at_step=step
                    )
                )

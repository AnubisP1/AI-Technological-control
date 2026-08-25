"""Доменная модель реального тулпаса и voxel-симуляции съёма материала
(Фаза 22, dev/PLAN.md) — заменяет статичные program_templates.py для
3-осевых призматических металлических деталей, для которых удалось
распознать топологию (см. app.domain.cad.feature_model.PartFeatureSet).

В отличие от SimulationPlan (Модуль 2, чистая UI-имитация одинаковым
текстом для любой детали данного типа операции), ToolpathPlan содержит
РЕАЛЬНО ВЫЧИСЛЕННЫЕ координаты движения инструмента и G-code, полученные
из конкретной геометрии детали и режимов резания конкретного материала/
инструмента — см. ToolpathGeneratorService.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ToolpathMove:
    kind: str  # 'rapid' | 'linear' | 'arc_cw' | 'arc_ccw'
    x_mm: float
    y_mm: float
    z_mm: float
    feed_mm_min: float | None = None  # None для rapid (движение на максимальной скорости)


@dataclass(frozen=True)
class ToolpathOperation:
    sequence_no: int
    feature_kind: str  # 'facing' | 'pocket' | 'hole'
    tool_diameter_mm: float
    tool_designation: str  # обозначение реального инструмента из tooling.designation (НСИ)
    spindle_speed_rpm: int
    feed_mm_min: float
    moves: tuple[ToolpathMove, ...] = field(default_factory=tuple)
    gcode_lines: tuple[str, ...] = field(default_factory=tuple)
    estimated_time_min: float = 0.0
    source_note: str = ""  # упрощение стратегии/допущение, если есть — не скрывается


@dataclass(frozen=True)
class ToolpathPlan:
    part_name: str | None
    stock_bounding_box_mm: tuple[float, float, float, float, float, float]  # x_min,x_max,y_min,y_max,z_min,z_max
    operations: tuple[ToolpathOperation, ...] = field(default_factory=tuple)
    unsupported_warning: str | None = None  # заполнено, если PartFeatureSet.is_supported=False
    warnings: tuple[str, ...] = field(default_factory=tuple)  # частные предупреждения (напр. инструмент не найден точно)

    @property
    def is_empty(self) -> bool:
        return len(self.operations) == 0


@dataclass(frozen=True)
class VoxelRemovalEvent:
    """Один воксель, удалённый на данном шаге симуляции — компактная
    sparse-запись вместо полного покадрового вывода (см.
    MaterialRemovalSimulator)."""

    voxel_x: int
    voxel_y: int
    voxel_z: int
    removed_at_step: int  # монотонно возрастающий индекс шага по всему ToolpathPlan


@dataclass(frozen=True)
class VoxelGridSpec:
    """Параметры воксельной сетки — фронтенд использует их, чтобы
    восстановить мировые координаты каждого вокселя из его индекса."""

    origin_mm: tuple[float, float, float]
    voxel_size_mm: float
    dims: tuple[int, int, int]  # nx, ny, nz


@dataclass(frozen=True)
class MaterialRemovalSimulation:
    grid: VoxelGridSpec
    events: tuple[VoxelRemovalEvent, ...] = field(default_factory=tuple)
    total_steps: int = 0

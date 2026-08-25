"""Оркестрация полного пайплайна реального CAM-тулпаса для металлических
деталей (Фаза 22, dev/PLAN.md): STEP -> топология -> распознанные фичи ->
тулпас -> voxel-симуляция съёма. Одна модульная функция для передачи в
run_heavy (ProcessPoolExecutor требует picklable callable — см.
worker_pool.py) — весь тяжёлый CPU-путь выполняется в одном воркере,
без нескольких отдельных обращений к пулу на каждый шаг.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.domain.manufacturing.toolpath_model import MaterialRemovalSimulation, ToolpathPlan
from app.infrastructure.cad.step_feature_extractor import extract_step_topology
from app.infrastructure.db.sqlite_process_planning_lookup import SqliteProcessPlanningLookup
from app.services.material_removal_simulator import simulate_material_removal
from app.services.toolpath_generator_service import ToolpathGeneratorService
from app.services.topology_feature_classifier import classify_topology


@dataclass(frozen=True)
class ToolpathPipelineResult:
    toolpath: ToolpathPlan
    simulation: MaterialRemovalSimulation | None
    """None, если тулпас пуст (unsupported_warning заполнен) — нечего симулировать."""


def run_toolpath_pipeline(
    *,
    step_path: Path,
    pythonocc_python_path: Path | None,
    metal_db_path: Path,
    part_name: str | None,
    material_grade: str | None,
) -> ToolpathPipelineResult:
    lookup = SqliteProcessPlanningLookup(metal_db_path)

    material_group_id = lookup.find_material_group_id(material_grade) if material_grade else None
    if material_group_id is None:
        toolpath = ToolpathPlan(
            part_name=part_name,
            stock_bounding_box_mm=(0, 0, 0, 0, 0, 0),
            operations=(),
            unsupported_warning=(
                f"Марка материала '{material_grade}' не найдена в справочнике НСИ — "
                "режимы резания рассчитать невозможно без известной группы материала."
                if material_grade
                else "Марка материала не распознана на чертеже — режимы резания рассчитать невозможно."
            ),
        )
        return ToolpathPipelineResult(toolpath=toolpath, simulation=None)

    topology = extract_step_topology(step_path, pythonocc_python_path)
    if topology is None:
        toolpath = ToolpathPlan(
            part_name=part_name,
            stock_bounding_box_mm=(0, 0, 0, 0, 0, 0),
            operations=(),
            unsupported_warning=(
                "Извлечение 3D-топологии недоступно (pythonocc-core не настроен на этой машине "
                "или не удалось разобрать STEP-файл) — автогенерация управляющей программы невозможна."
            ),
        )
        return ToolpathPipelineResult(toolpath=toolpath, simulation=None)

    feature_set = classify_topology(topology)
    generator = ToolpathGeneratorService(lookup)
    toolpath = generator.generate(
        part_name=part_name,
        feature_set=feature_set,
        material_group_id=material_group_id,
        bounding_box_mm=topology.bounding_box_mm,
    )

    if toolpath.is_empty:
        return ToolpathPipelineResult(toolpath=toolpath, simulation=None)

    simulation = simulate_material_removal(toolpath)
    return ToolpathPipelineResult(toolpath=toolpath, simulation=simulation)

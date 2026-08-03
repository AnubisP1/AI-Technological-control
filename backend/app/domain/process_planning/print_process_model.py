"""Доменные структуры техпроцесса печати, подобранного по правилам
совместимости для аддитивных технологий (Модуль 1.3, пластик).

В отличие от металла, на вход для пластиковых изделий по ТЗ подаётся
только STEP-модель без чертежа — материал и технология печати не
извлекаются из документа (взять их неоткуда), а указываются
пользователем явно при запуске анализа (см. dev/QUESTIONS.md).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PlannedPostprocessingStep:
    sequence_no: int
    pp_tooling_type_name: str
    is_required: bool
    quality_effect_note: str | None = None


@dataclass(frozen=True)
class PrintQualityStandard:
    """Допуски/шероховатость по технологии печати (Модуль 1.3, пластик) —
    из am_technology_tolerance, для отображения в карте техпроцесса печати
    как справочных дизайн-правил, не рассчитываемых автоподбором."""

    tolerance_mm: str
    min_wall_thickness_mm: str
    roughness_ra_raw_um: str
    roughness_ra_finished_um: str | None
    min_thread_pitch_mm: str | None
    assembly_clearance_mm: str | None
    source_note: str


@dataclass(frozen=True)
class PrintEstimate:
    """Оценка параметров печати (высота слоя/время/расход материала) —
    Фаза 17, по объёму STEP bounding box детали (не по истинному объёму
    тела — тесселяция геометрии не строится, см. dev/PLAN.md), поэтому
    явно помечена как оценка по габаритному объёму, а не точный расчёт
    по слайсеру."""

    layer_height_mm: float
    estimated_print_time_min: float
    estimated_material_g: float
    source_note: str


@dataclass(frozen=True)
class PrintProcessPlanningResult:
    part_name: str | None
    am_technology_code: str
    am_material_group_name: str | None
    printer_model_name: str | None
    postprocessing_steps: tuple[PlannedPostprocessingStep, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)
    quality_standard: PrintQualityStandard | None = None
    print_estimate: PrintEstimate | None = None

    @property
    def is_empty(self) -> bool:
        return self.am_material_group_name is None

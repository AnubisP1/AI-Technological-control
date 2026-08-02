"""Доменные структуры автоподбора материала для пластиковых изделий
(Модуль 1.3, Фаза 10) — по классу применения детали (part_application_class)
и типичным условиям эксплуатации (operating_condition), без ручного выбора
технологии/материала пользователем.

Источник рекомендаций — уже засеянная таблица
application_material_recommendation (additive-НСИ), с явной пометкой
источника и его надёжности (recommendation_source) — не выдаётся за
производственный расчёт, community_practice остаётся community_practice
и в выводе API.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class MaterialRecommendationOption:
    priority: int
    am_technology_code: str
    am_technology_name: str
    material_group_code: str
    material_group_name: str
    rationale: str
    source_type: str
    source_title: str
    source_reliability: str
    min_infill_percent: float | None
    recommended_wall_count: int | None
    orientation_note: str | None


@dataclass(frozen=True)
class MaterialRecommendationResult:
    part_application_class_code: str
    matched_operating_conditions: tuple[str, ...]
    options: tuple[MaterialRecommendationOption, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)

    @property
    def is_empty(self) -> bool:
        return len(self.options) == 0

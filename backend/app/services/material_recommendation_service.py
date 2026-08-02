"""Сервис автоподбора материала для пластиковых изделий по классу
применения детали и условиям эксплуатации (Модуль 1.3, Фаза 10,
БПЛА-домен) — заменяет ручной выбор технологии/материала пользователем
для пластика, как того требует ключевое требование фронтенд-плана.

Как и остальной автоподбор (Фаза 4): не выдумывает рекомендацию, если
её нет в БД — при отсутствии данных под конкретные условия эксплуатации
явно откатывается на базовые рекомендации класса детали (не привязанные
ни к каким условиям) с предупреждением, а не молчит и не изобретает.
"""

from __future__ import annotations

from app.domain.process_planning.material_recommendation_model import (
    MaterialRecommendationOption,
    MaterialRecommendationResult,
)
from app.domain.process_planning.print_planning_lookup_port import IPrintPlanningLookup


class MaterialRecommendationService:
    def __init__(self, lookup: IPrintPlanningLookup) -> None:
        self._lookup = lookup

    def recommend(
        self, *, part_application_class_code: str, operating_condition_codes: tuple[str, ...]
    ) -> MaterialRecommendationResult:
        part_class = self._lookup.find_part_application_class_by_code(
            part_application_class_code
        )
        if part_class is None:
            return MaterialRecommendationResult(
                part_application_class_code=part_application_class_code,
                matched_operating_conditions=(),
                warnings=(
                    f"Класс применения детали '{part_application_class_code}' не найден "
                    "в справочнике НСИ — автоподбор материала невозможен.",
                ),
            )

        warnings: list[str] = []
        code_to_id = self._lookup.find_operating_condition_ids_by_codes(
            operating_condition_codes
        )
        unmatched_codes = tuple(
            code for code in operating_condition_codes if code not in code_to_id
        )
        if unmatched_codes:
            warnings.append(
                "Не найдены в справочнике условия эксплуатации: "
                + ", ".join(unmatched_codes)
            )

        matched_codes = tuple(code for code in operating_condition_codes if code in code_to_id)
        condition_ids = tuple(code_to_id[code] for code in matched_codes)

        rows = self._lookup.find_material_recommendations(part_class.id, condition_ids)
        matched_conditions = matched_codes if condition_ids else ()

        if not rows and condition_ids:
            warnings.append(
                "Нет рекомендаций для указанных условий эксплуатации — показана "
                "базовая рекомендация без учёта условий эксплуатации, "
                "требуется проверка технологом."
            )
            rows = self._lookup.find_material_recommendations(part_class.id, ())
            matched_conditions = ()

        if not rows:
            warnings.append(
                f"Для класса '{part_class.name}' нет ни одной рекомендации материала "
                "в справочнике НСИ — автоподбор не дал результата."
            )

        options = tuple(
            MaterialRecommendationOption(
                priority=row.priority,
                am_technology_code=row.am_technology_code,
                am_technology_name=row.am_technology_name,
                material_group_code=row.material_group_code,
                material_group_name=row.material_group_name,
                rationale=row.rationale,
                source_type=row.source_type,
                source_title=row.source_title,
                source_reliability=row.source_reliability,
                min_infill_percent=row.min_infill_percent,
                recommended_wall_count=row.recommended_wall_count,
                orientation_note=row.orientation_note,
            )
            for row in rows
        )

        return MaterialRecommendationResult(
            part_application_class_code=part_application_class_code,
            matched_operating_conditions=matched_conditions,
            options=options,
            warnings=tuple(warnings),
        )

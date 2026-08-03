"""Расчёт параметров печати (высота слоя, время печати, расход
материала) — Фаза 17, по явному запросу пользователя ("нужен точный
расчёт... параметров печати", 2026-08-03).

Высота слоя — середина диапазона layer_resolution_min/max_mm технологии
(am_technology_tolerance, Фаза 9.5). Объём детали — оценка по
габаритному объёму bounding box STEP (length_x*y*z), умноженному на
коэффициент эффективного заполнения (_EFFECTIVE_VOLUME_FRACTION):
реальная деталь почти всегда занимает лишь часть своего параллелепипеда
(тонкостенные корпуса, частичный infill) — без тесселяции геометрии
(pythonocc-core не подключён, см. dev/PLAN.md) невозможно посчитать
точный объём тела, поэтому применяется единый консервативный
коэффициент вместо выдачи заведомо завышенной оценки по полному
параллелепипеду. Явно помечено в source_note как приближение, не
точный расчёт по слайсеру. Масса — эффективный объём * плотность
материала (am_material.density_g_cm3). Время печати — тот же объём,
делённый на типовую объёмную производительность технологии
(print_speed_reference).
"""

from __future__ import annotations

from app.domain.cad.step_model import BoundingBox
from app.domain.process_planning.print_planning_lookup_port import IPrintPlanningLookup
from app.domain.process_planning.print_process_model import PrintEstimate

_SECONDS_PER_MINUTE = 60

# Типовая доля объёма параллелепипеда bounding box, реально занимаемая
# материалом печатной детали (стенки + умеренный infill) — инженерный
# ориентир для деталей корпусного типа (не сплошной куб, не проволочный
# каркас), взят как консервативная середина диапазона 15-35%, типичного
# для FDM-печати с 15-20% infill и типовой толщиной стенок 2-4 периметра.
_EFFECTIVE_VOLUME_FRACTION = 0.25


class PrintParameterCalculator:
    def __init__(self, lookup: IPrintPlanningLookup) -> None:
        self._lookup = lookup

    def calculate(
        self,
        *,
        am_technology_id: int,
        am_material_group_id: int,
        bounding_box: BoundingBox | None,
    ) -> PrintEstimate | None:
        if bounding_box is None:
            return None

        tolerance = self._lookup.find_technology_tolerance(am_technology_id)
        density = self._lookup.find_material_density(am_material_group_id)
        speed_ref = self._lookup.find_print_speed_reference(am_technology_id)
        if tolerance is None or density is None or speed_ref is None:
            return None

        layer_height_mm = (tolerance.layer_resolution_min_mm + tolerance.layer_resolution_max_mm) / 2

        bbox_volume_mm3 = bounding_box.length_x * bounding_box.length_y * bounding_box.length_z
        effective_volume_mm3 = bbox_volume_mm3 * _EFFECTIVE_VOLUME_FRACTION
        material_g = (effective_volume_mm3 / 1000) * density.density_g_cm3

        print_time_seconds = effective_volume_mm3 / speed_ref.volumetric_rate_mm3_s
        print_time_min = print_time_seconds / _SECONDS_PER_MINUTE

        return PrintEstimate(
            layer_height_mm=round(layer_height_mm, 3),
            estimated_print_time_min=round(print_time_min, 1),
            estimated_material_g=round(material_g, 1),
            source_note=(
                f"Оценка по {_EFFECTIVE_VOLUME_FRACTION:.0%} объёма параллелепипеда "
                f"bounding box STEP ({bounding_box.length_x:g}×{bounding_box.length_y:g}×"
                f"{bounding_box.length_z:g} мм) — приближение эффективного объёма "
                "материала детали (стенки + типовой infill), не точный объём тела "
                "(тесселяция геометрии не строится); "
                f"плотность материала {density.density_g_cm3:g} г/см³; "
                f"{speed_ref.source}"
            ),
        )

"""Генератор реального 3-осевого фрезерного тулпаса для распознанных
призматических фич (Фаза 22, dev/PLAN.md) — заменяет статичные
program_templates.py для металлических деталей с топологией.

Режимы резания считаются ЗДЕСЬ, а не через существующий
CuttingModeCalculator (Фаза 17) — тот рассчитан на диаметр КРУГЛОЙ
ЗАГОТОВКИ (точение/сверление сплошного прутка), что физически неверно
для фрезерования/сверления призматической плиты (там нет диаметра
заготовки вообще — заготовка прямоугольная). Формула скорости резания
V=Cv/(T^m·t^xv·S^yv)·Kv и её коэффициенты (cutting_mode_formula,
feed_reference) — те же самые, источники те же (см.
cutting_mode_calculator.py) — но обороты шпинделя считаются по диаметру
РЕЖУЩЕГО ИНСТРУМЕНТА (n=1000·V/(π·D_инструмента)), не диаметру заготовки,
что физически корректно для фрезерования/сверления в любом случае.

Подбор инструмента — из реально засеянных tooling НСИ (find_tooling_by_type_code),
ближайший диаметр к требуемому. Если требуемый диаметр (напр. отверстия)
больше самого крупного засеянного сверла — отверстие фрезеруется круговой
интерполяцией имеющейся концевой фрезой (реальная, широко применяемая
технологическая стратегия для отверстий вне диапазона доступных свёрл, не
аппроксимация "как получится" — явно помечается в source_note).
"""

from __future__ import annotations

import math

from app.domain.cad.feature_model import PartFeatureSet
from app.domain.manufacturing.toolpath_model import ToolpathMove, ToolpathOperation, ToolpathPlan
from app.domain.process_planning.process_planning_lookup_port import IProcessPlanningLookup, ToolingRecord

_STOCK_MARGIN_MM = 3.0  # припуск заготовки поверх габарита готовой детали — типовое значение для плитового проката
_SAFE_Z_CLEARANCE_MM = 5.0  # безопасная высота отвода инструмента над деталью
_PECK_DEPTH_RATIO = 3.0  # сверление с выводом стружки при глубине > 3×диаметра — реальное технологическое правило
_PECK_STEP_MM = 5.0

_MILL_TOOLING_TYPE_CODE = "MILL_END"
_DRILL_TOOLING_TYPE_CODE = "DRILL_TWIST"
_CIRCLE_SEGMENTS = 32  # полигональная аппроксимация окружности для кругового фрезерования отверстий


class ToolpathGenerationError(RuntimeError):
    """Поднимается, когда тулпас в принципе нельзя посчитать (нет
    коэффициентов режимов резания в НСИ и т.п.) — вызывающий сервис
    обязан превратить это в честное предупреждение, не молчаливый пропуск."""


class ToolpathGeneratorService:
    def __init__(self, lookup: IProcessPlanningLookup) -> None:
        self._lookup = lookup

    def generate(
        self,
        *,
        part_name: str | None,
        feature_set: PartFeatureSet,
        material_group_id: int,
        bounding_box_mm: tuple[float, float, float, float, float, float],
    ) -> ToolpathPlan:
        if not feature_set.is_supported:
            return ToolpathPlan(
                part_name=part_name,
                stock_bounding_box_mm=bounding_box_mm,
                operations=(),
                unsupported_warning=(
                    "Геометрия детали не распознана как 3-осевая призматическая заготовка "
                    "(похоже на тело вращения либо преимущественно непокрытые v1 поверхности) — "
                    "автогенерация управляющей программы недоступна, требуется технолог-программист."
                ),
            )

        stock_bbox = _expand_bounding_box(bounding_box_mm, _STOCK_MARGIN_MM)
        top_z_mm = bounding_box_mm[5]

        operations: list[ToolpathOperation] = []
        warnings: list[str] = []
        sequence_no = 1

        top_facing_faces = [f for f in feature_set.millable_faces if f.normal_up]
        if top_facing_faces:
            try:
                op = self._generate_facing_operation(
                    sequence_no=sequence_no,
                    material_group_id=material_group_id,
                    stock_bbox=stock_bbox,
                    z_height_mm=top_z_mm,
                )
                operations.append(op)
                sequence_no += 1
            except ToolpathGenerationError as exc:
                warnings.append(str(exc))

        for hole in feature_set.holes:
            try:
                op = self._generate_hole_operation(
                    sequence_no=sequence_no,
                    material_group_id=material_group_id,
                    hole=hole,
                    top_z_mm=top_z_mm,
                )
                operations.append(op)
                sequence_no += 1
            except ToolpathGenerationError as exc:
                warnings.append(str(exc))

        return ToolpathPlan(
            part_name=part_name,
            stock_bounding_box_mm=stock_bbox,
            operations=tuple(operations),
            unsupported_warning=None,
            warnings=tuple(warnings),
        )

    def _calculate_spindle_and_feed(
        self, *, operation_type_code: str, material_group_id: int, tool_diameter_mm: float
    ) -> tuple[float, int, float, str]:
        """Возвращает (cutting_speed_m_min, spindle_speed_rpm, feed_mm_min, source_note)."""
        operation_type_id = self._lookup.find_operation_type_id_by_code(operation_type_code)
        if operation_type_id is None:
            raise ToolpathGenerationError(f"В справочнике нет типа операции '{operation_type_code}'.")

        formula = self._lookup.find_cutting_mode_formula(operation_type_id)
        if formula is None:
            raise ToolpathGenerationError(
                f"Для операции '{operation_type_code}' в справочнике нет коэффициентов формулы режимов резания."
            )

        feed_ref = self._lookup.find_feed_reference(operation_type_id, material_group_id)
        if feed_ref is None:
            raise ToolpathGenerationError(
                f"Для операции '{operation_type_code}' и данной группы материала нет типовой подачи/глубины резания."
            )

        machinability = self._lookup.find_material_machinability(material_group_id)
        kv = machinability.machinability_index if machinability is not None else 1.0

        feed_mm_rev = (feed_ref.feed_mm_rev_min + feed_ref.feed_mm_rev_max) / 2
        if feed_ref.depth_of_cut_mm_min is not None and feed_ref.depth_of_cut_mm_max is not None:
            depth_of_cut_mm = (feed_ref.depth_of_cut_mm_min + feed_ref.depth_of_cut_mm_max) / 2
        else:
            depth_of_cut_mm = tool_diameter_mm / 2  # сверление сплошного отверстия — глубина резания = радиус инструмента

        cutting_speed_m_min = (
            formula.cv / (formula.tool_life_min**formula.m * depth_of_cut_mm**formula.xv * feed_mm_rev**formula.yv) * kv
        )
        spindle_speed_rpm = round(1000 * cutting_speed_m_min / (math.pi * tool_diameter_mm))
        # Подача на оборот -> подача в минуту через реальные обороты шпинделя
        # этого инструмента (не диаметра заготовки — см. docstring модуля).
        feed_mm_min = round(feed_mm_rev * spindle_speed_rpm, 1)

        source_note = f"{formula.source}; {feed_ref.source}"
        return cutting_speed_m_min, spindle_speed_rpm, feed_mm_min, source_note

    def _select_tool(self, *, tooling_type_code: str, target_diameter_mm: float | None) -> ToolingRecord:
        candidates = self._lookup.find_tooling_by_type_code(tooling_type_code)
        if not candidates:
            raise ToolpathGenerationError(
                f"В справочнике НСИ нет ни одного инструмента типа '{tooling_type_code}'."
            )
        if target_diameter_mm is None:
            return min(candidates, key=lambda t: -t.diameter_mm)  # для facing — берём самый крупный доступный
        return min(candidates, key=lambda t: abs(t.diameter_mm - target_diameter_mm))

    def _generate_facing_operation(
        self,
        *,
        sequence_no: int,
        material_group_id: int,
        stock_bbox: tuple[float, float, float, float, float, float],
        z_height_mm: float,
    ) -> ToolpathOperation:
        tool = self._select_tool(tooling_type_code=_MILL_TOOLING_TYPE_CODE, target_diameter_mm=None)
        _, spindle_rpm, feed_mm_min, source_note = self._calculate_spindle_and_feed(
            operation_type_code="MILL", material_group_id=material_group_id, tool_diameter_mm=tool.diameter_mm
        )

        x_min, x_max, y_min, y_max = stock_bbox[0], stock_bbox[1], stock_bbox[2], stock_bbox[3]
        safe_z = z_height_mm + _SAFE_Z_CLEARANCE_MM
        step_over_mm = tool.diameter_mm * 0.7  # перекрытие проходов ~30% — типовое значение для торцевого фрезерования

        moves: list[ToolpathMove] = [ToolpathMove(kind="rapid", x_mm=x_min, y_mm=y_min, z_mm=safe_z)]
        moves.append(ToolpathMove(kind="rapid", x_mm=x_min, y_mm=y_min, z_mm=z_height_mm))

        y = y_min
        direction_forward = True
        while y <= y_max + 1e-6:
            x_start, x_end = (x_min, x_max) if direction_forward else (x_max, x_min)
            moves.append(ToolpathMove(kind="linear", x_mm=x_start, y_mm=y, z_mm=z_height_mm, feed_mm_min=feed_mm_min))
            moves.append(ToolpathMove(kind="linear", x_mm=x_end, y_mm=y, z_mm=z_height_mm, feed_mm_min=feed_mm_min))
            y += step_over_mm
            direction_forward = not direction_forward

        moves.append(ToolpathMove(kind="rapid", x_mm=moves[-1].x_mm, y_mm=moves[-1].y_mm, z_mm=safe_z))

        gcode_lines = _moves_to_gcode(moves, spindle_rpm=spindle_rpm, comment="Торцевое фрезерование верхней грани")
        path_length_mm = _path_length(moves)
        estimated_time_min = path_length_mm / feed_mm_min if feed_mm_min > 0 else 0.0

        return ToolpathOperation(
            sequence_no=sequence_no,
            feature_kind="facing",
            tool_diameter_mm=tool.diameter_mm,
            tool_designation=tool.designation,
            spindle_speed_rpm=spindle_rpm,
            feed_mm_min=feed_mm_min,
            moves=tuple(moves),
            gcode_lines=gcode_lines,
            estimated_time_min=round(estimated_time_min, 2),
            source_note=source_note,
        )

    def _generate_hole_operation(
        self, *, sequence_no: int, material_group_id: int, hole, top_z_mm: float
    ) -> ToolpathOperation:
        drills = self._lookup.find_tooling_by_type_code(_DRILL_TOOLING_TYPE_CODE)
        exact_drill = next((d for d in drills if abs(d.diameter_mm - hole.diameter_mm) < 0.5), None)

        if exact_drill is not None:
            return self._generate_drilling(sequence_no, material_group_id, hole, top_z_mm, exact_drill)
        return self._generate_hole_by_circular_milling(sequence_no, material_group_id, hole, top_z_mm)

    def _generate_drilling(self, sequence_no, material_group_id, hole, top_z_mm, tool: ToolingRecord) -> ToolpathOperation:
        _, spindle_rpm, feed_mm_min, source_note = self._calculate_spindle_and_feed(
            operation_type_code="DRILL", material_group_id=material_group_id, tool_diameter_mm=tool.diameter_mm
        )
        cx, cy = hole.center_xy_mm
        safe_z = top_z_mm + _SAFE_Z_CLEARANCE_MM
        bottom_z = top_z_mm - hole.depth_mm

        moves = [
            ToolpathMove(kind="rapid", x_mm=cx, y_mm=cy, z_mm=safe_z),
        ]
        if hole.depth_mm > _PECK_DEPTH_RATIO * tool.diameter_mm:
            # Сверление с выводом стружки (peck drilling) — реальное
            # технологическое правило при глубоком отверстии, не выдуманный шаг.
            current_z = top_z_mm
            while current_z > bottom_z:
                current_z = max(bottom_z, current_z - _PECK_STEP_MM)
                moves.append(ToolpathMove(kind="linear", x_mm=cx, y_mm=cy, z_mm=current_z, feed_mm_min=feed_mm_min))
                moves.append(ToolpathMove(kind="rapid", x_mm=cx, y_mm=cy, z_mm=safe_z))
                if current_z > bottom_z:
                    moves.append(ToolpathMove(kind="rapid", x_mm=cx, y_mm=cy, z_mm=current_z + _PECK_STEP_MM))
        else:
            moves.append(ToolpathMove(kind="linear", x_mm=cx, y_mm=cy, z_mm=bottom_z, feed_mm_min=feed_mm_min))

        moves.append(ToolpathMove(kind="rapid", x_mm=cx, y_mm=cy, z_mm=safe_z))

        gcode_lines = _moves_to_gcode(moves, spindle_rpm=spindle_rpm, comment=f"Сверление отверстия Ø{hole.diameter_mm}")
        estimated_time_min = _path_length(moves) / feed_mm_min if feed_mm_min > 0 else 0.0

        return ToolpathOperation(
            sequence_no=sequence_no,
            feature_kind="hole",
            tool_diameter_mm=tool.diameter_mm,
            tool_designation=tool.designation,
            spindle_speed_rpm=spindle_rpm,
            feed_mm_min=feed_mm_min,
            moves=tuple(moves),
            gcode_lines=gcode_lines,
            estimated_time_min=round(estimated_time_min, 2),
            source_note=source_note,
        )

    def _generate_hole_by_circular_milling(self, sequence_no, material_group_id, hole, top_z_mm) -> ToolpathOperation:
        tool = self._select_tool(tooling_type_code=_MILL_TOOLING_TYPE_CODE, target_diameter_mm=hole.diameter_mm * 0.5)
        if tool.diameter_mm >= hole.diameter_mm:
            raise ToolpathGenerationError(
                f"Нет инструмента в НСИ достаточно малого диаметра для фрезерования отверстия Ø{hole.diameter_mm} "
                f"круговой интерполяцией (доступная фреза Ø{tool.diameter_mm})."
            )

        _, spindle_rpm, feed_mm_min, source_note = self._calculate_spindle_and_feed(
            operation_type_code="MILL", material_group_id=material_group_id, tool_diameter_mm=tool.diameter_mm
        )
        cx, cy = hole.center_xy_mm
        safe_z = top_z_mm + _SAFE_Z_CLEARANCE_MM
        bottom_z = top_z_mm - hole.depth_mm
        orbit_radius_mm = hole.diameter_mm / 2 - tool.diameter_mm / 2
        entry_x = cx + orbit_radius_mm

        moves = [
            ToolpathMove(kind="rapid", x_mm=entry_x, y_mm=cy, z_mm=safe_z),
            ToolpathMove(kind="linear", x_mm=entry_x, y_mm=cy, z_mm=bottom_z, feed_mm_min=feed_mm_min),
        ]
        # Полный круг как последовательность линейных сегментов — v1
        # постпроцессора выводит только G0/G1 (см. _moves_to_gcode
        # docstring), полноценная дуговая интерполяция в тексте программы
        # не покрыта этой версией.
        for i in range(1, _CIRCLE_SEGMENTS + 1):
            angle = 2 * math.pi * i / _CIRCLE_SEGMENTS
            seg_x = cx + orbit_radius_mm * math.cos(angle)
            seg_y = cy + orbit_radius_mm * math.sin(angle)
            moves.append(ToolpathMove(kind="linear", x_mm=seg_x, y_mm=seg_y, z_mm=bottom_z, feed_mm_min=feed_mm_min))
        moves.append(ToolpathMove(kind="rapid", x_mm=entry_x, y_mm=cy, z_mm=safe_z))

        gcode_lines = _moves_to_gcode(
            moves,
            spindle_rpm=spindle_rpm,
            comment=f"Фрезерование отверстия Ø{hole.diameter_mm} круговой интерполяцией (нет сверла нужного диаметра в НСИ)",
        )
        circumference_mm = math.pi * hole.diameter_mm
        estimated_time_min = (circumference_mm + hole.depth_mm) / feed_mm_min if feed_mm_min > 0 else 0.0

        return ToolpathOperation(
            sequence_no=sequence_no,
            feature_kind="hole",
            tool_diameter_mm=tool.diameter_mm,
            tool_designation=tool.designation,
            spindle_speed_rpm=spindle_rpm,
            feed_mm_min=feed_mm_min,
            moves=tuple(moves),
            gcode_lines=gcode_lines,
            estimated_time_min=round(estimated_time_min, 2),
            source_note=(
                f"{source_note}; отверстие получено круговой интерполяцией концевой фрезой "
                f"Ø{tool.diameter_mm} — в НСИ нет сверла подходящего диаметра"
            ),
        )


def _expand_bounding_box(
    bbox: tuple[float, float, float, float, float, float], margin_mm: float
) -> tuple[float, float, float, float, float, float]:
    x_min, x_max, y_min, y_max, z_min, z_max = bbox
    return (x_min - margin_mm, x_max + margin_mm, y_min - margin_mm, y_max + margin_mm, z_min, z_max)


def _path_length(moves: tuple[ToolpathMove, ...] | list[ToolpathMove]) -> float:
    total = 0.0
    for prev, curr in zip(moves, moves[1:]):
        total += math.sqrt((curr.x_mm - prev.x_mm) ** 2 + (curr.y_mm - prev.y_mm) ** 2 + (curr.z_mm - prev.z_mm) ** 2)
    return total


def _moves_to_gcode(moves: tuple[ToolpathMove, ...] | list[ToolpathMove], *, spindle_rpm: int, comment: str) -> tuple[str, ...]:
    """Fanuc-подобный постпроцессор — G0/G1 (без G2/G3 текстового вывода
    для v1: круговая интерполяция v1 выводится как линейные подходы,
    полноценная дуговая интерполяция в тексте программы — за рамками
    этой версии, честно ограничено простыми линейными/быстрыми ходами)."""
    lines = [f"; {comment}", f"M03 S{spindle_rpm}"]
    for move in moves:
        if move.kind == "rapid":
            lines.append(f"G0 X{move.x_mm:.3f} Y{move.y_mm:.3f} Z{move.z_mm:.3f}")
        else:
            feed = f" F{move.feed_mm_min:.1f}" if move.feed_mm_min else ""
            lines.append(f"G1 X{move.x_mm:.3f} Y{move.y_mm:.3f} Z{move.z_mm:.3f}{feed}")
    lines.append("M05")
    return tuple(lines)

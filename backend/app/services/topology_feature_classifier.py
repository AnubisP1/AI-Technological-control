"""Классификация сырой топологии STEP (PartTopology) в обрабатываемые
фрезерованием фичи (PartFeatureSet) — Фаза 22, dev/PLAN.md.

Правила классификации:
- Сначала проверяется, не тело ли это вращения (вал и подобные детали —
  область точения, не 3-осевого фрезерования, вне объёма v1 по решению
  пользователя: "вал делается не фрезерованием, а точением"). Признак —
  доля полнооборотных цилиндрических граней с ОБЩЕЙ осью среди всех
  цилиндрических граней детали: у вала это внешняя поверхность ступеней
  (материал внутри), геометрически неотличимая от отверстия (материал
  снаружи) по одному только диаметру — размерная эвристика на этом
  ломается (было эмпирически найдено на реальном fixture "Вал": ступени
  Ø45-65мм при поперечном габарите 65мм классифицировались как ложные
  отверстия). Доля цилиндров на общей оси — надёжный сигнал именно
  потому, что у вала таких ступеней МНОГО и они соосны, а у призматической
  детали с отверстиями каждый цилиндр — самостоятельная не связанная
  этой закономерностью фича (проверено на всех трёх fixture проекта, см.
  ниже пороги).
- Если деталь не тело вращения: цилиндрическая грань с полным угловым
  охватом (is_full_turn=True) — сквозное/глухое отверстие. Частичный
  охват (галтель/скругление кромки, is_full_turn=False) — не фича v1.
- Плоская грань с нормалью вдоль оси Z детали (|normal.z| близко к 1) —
  обрабатываемая сверху/снизу грань (facing). Боковые плоские грани не
  выделяются как самостоятельная фича v1 (нужно распознавание карманов
  как составной фичи — не покрыто демо-fixture, см. dev/QUESTIONS.md).
- other_face_count (конусы/сплайны — фаски, сложные поверхности) —
  всегда unrecognized, но НЕ блокирует поддержку детали целиком: фаски
  на кромках — обычная конструктивная деталь (найдено на Кронштейн.STEP:
  9 фасок + 4 галтели — 65% граней "прочие", деталь при этом полностью
  обрабатываемая 3-осевым фрезерованием).

is_supported=False когда деталь — тело вращения ИЛИ классификация не
дала ни одной millable_face и ни одного отверстия.
"""

from __future__ import annotations

from app.domain.cad.feature_model import CylindricalFace, MillableFace, PartFeatureSet, PartTopology, RecognizedHole

_Z_ALIGNMENT_COS_THRESHOLD = 0.9  # нормаль отклоняется от оси Z не более чем на ~25°
_AXIS_ALIGNMENT_COS_THRESHOLD = 0.9  # ось цилиндра "почти точно" совпадает с одной из осей X/Y/Z
_AXIS_MATCH_TOLERANCE = 0.05  # два направления считаются "одной осью", если компоненты совпадают в пределах этого допуска

# Порог отнесения детали к телам вращения (см. docstring модуля) — 0.60
# у реального "Вала" против 0.20 у "Кронштейна" и 0.04 у "Шестерни",
# порог 0.4 разделяет их с большим запасом на всех трёх fixture проекта.
_REVOLVED_BODY_SHARE_THRESHOLD = 0.4
_REVOLVED_BODY_MIN_COAXIAL_COUNT = 3  # деталь с 1-2 соосными цилиндрами — не обязательно тело вращения

# Доля габарита вдоль оси отверстия, которую должна покрывать цилиндрическая
# грань, чтобы отверстие считалось сквозным. Не 0.9-0.95 — типичная фаска
# на входе в отверстие "съедает" часть цилиндрической грани у кромки
# (найдено на реальном fixture Кронштейн.STEP: грань отверстия 17мм при
# габарите детали 20мм в направлении оси отверстия — визуально сквозное
# отверстие, разница целиком объясняется фаской на входе).
_THROUGH_HOLE_AXIS_COVERAGE_RATIO = 0.8


def _normalized_axis_key(direction: tuple[float, float, float]) -> tuple[float, float, float]:
    """Нормализует знак направления оси, чтобы (1,0,0) и (-1,0,0)
    считались одной и той же осью (ориентация грани, не ось детали)."""
    x, y, z = direction
    flip = x < -_AXIS_MATCH_TOLERANCE or (
        abs(x) <= _AXIS_MATCH_TOLERANCE
        and (y < -_AXIS_MATCH_TOLERANCE or (abs(y) <= _AXIS_MATCH_TOLERANCE and z < -_AXIS_MATCH_TOLERANCE))
    )
    if flip:
        x, y, z = -x, -y, -z
    return (round(x, 2), round(y, 2), round(z, 2))


def _is_revolved_body(cylindrical_faces: tuple[CylindricalFace, ...]) -> bool:
    if not cylindrical_faces:
        return False
    full_turn = [c for c in cylindrical_faces if c.is_full_turn]
    if not full_turn:
        return False

    axis_counts: dict[tuple[float, float, float], int] = {}
    for cyl in full_turn:
        key = _normalized_axis_key(cyl.axis_direction)
        axis_counts[key] = axis_counts.get(key, 0) + 1

    dominant_count = max(axis_counts.values())
    share = dominant_count / len(cylindrical_faces)
    return dominant_count >= _REVOLVED_BODY_MIN_COAXIAL_COUNT and share >= _REVOLVED_BODY_SHARE_THRESHOLD


def _axis_span_mm(
    bbox: tuple[float, float, float, float, float, float], axis_direction: tuple[float, float, float]
) -> float | None:
    """Габарит детали вдоль оси цилиндра — None, если ось не выровнена
    ни по одной из осей X/Y/Z (тогда честно не считаем through, не гадаем)."""
    spans = {"x": bbox[1] - bbox[0], "y": bbox[3] - bbox[2], "z": bbox[5] - bbox[4]}
    ax, ay, az = axis_direction
    if abs(ax) >= _AXIS_ALIGNMENT_COS_THRESHOLD:
        return spans["x"]
    if abs(ay) >= _AXIS_ALIGNMENT_COS_THRESHOLD:
        return spans["y"]
    if abs(az) >= _AXIS_ALIGNMENT_COS_THRESHOLD:
        return spans["z"]
    return None


def classify_topology(topology: PartTopology) -> PartFeatureSet:
    bbox = topology.bounding_box_mm

    if _is_revolved_body(topology.cylindrical_faces):
        return PartFeatureSet(
            unrecognized_face_count=topology.total_face_count,
            total_face_count=topology.total_face_count,
            is_supported=False,
        )

    millable_faces = tuple(
        MillableFace(z_height_mm=face.origin_mm[2], normal_up=face.normal[2] > 0)
        for face in topology.planar_faces
        if abs(face.normal[2]) >= _Z_ALIGNMENT_COS_THRESHOLD
    )

    holes: list[RecognizedHole] = []
    unrecognized_from_cylinders = 0
    for cyl in topology.cylindrical_faces:
        if cyl.is_full_turn:
            axis_span_mm = _axis_span_mm(bbox, cyl.axis_direction)
            holes.append(
                RecognizedHole(
                    center_xy_mm=(cyl.axis_origin_mm[0], cyl.axis_origin_mm[1]),
                    diameter_mm=round(2 * cyl.radius_mm, 3),
                    depth_mm=round(cyl.height_mm, 3),
                    # Различить сквозное/глухое отверстие по одной грани нельзя
                    # без сопоставления с противоположной стороной детали — не
                    # выдумываем, считаем сквозным консервативно только когда
                    # глубина отверстия покрывает почти весь габарит детали
                    # вдоль оси самого отверстия.
                    through=(
                        axis_span_mm is not None
                        and cyl.height_mm >= _THROUGH_HOLE_AXIS_COVERAGE_RATIO * axis_span_mm
                    ),
                )
            )
        else:
            unrecognized_from_cylinders += 1

    unrecognized_from_planes = len(topology.planar_faces) - len(millable_faces)
    unrecognized_face_count = (
        unrecognized_from_planes + unrecognized_from_cylinders + topology.other_face_count
    )

    is_supported = len(millable_faces) > 0 or len(holes) > 0

    return PartFeatureSet(
        millable_faces=millable_faces,
        holes=tuple(holes),
        unrecognized_face_count=unrecognized_face_count,
        total_face_count=topology.total_face_count,
        is_supported=is_supported,
    )

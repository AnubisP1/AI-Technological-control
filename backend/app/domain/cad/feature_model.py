"""Доменные структуры топологии и распознанных обрабатываемых фич STEP-
модели (Фаза 22 — реальный CAM-тулпас, dev/PLAN.md).

Два слоя намеренно разделены:
- PartTopology — сырой результат обхода B-rep (грани по типу поверхности,
  как их видит OpenCASCADE), не зависит от способа извлечения (см.
  IStepFeatureExtractor в step_feature_extractor_port.py).
- PartFeatureSet — результат КЛАССИФИКАЦИИ топологии в обрабатываемые
  фрезерованием сущности (сквозное отверстие vs галтель-скругление,
  прямоугольный карман и т.д.) — это доменная бизнес-логика
  (TopologyFeatureClassifier), не часть парсинга.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PlanarFace:
    """Плоская грань как её видит OpenCASCADE — точка на плоскости,
    нормаль, протяжённость по параметрам поверхности (не физические
    габариты контура, а диапазон U/V — используется классификатором как
    вспомогательный сигнал, не единственный)."""

    origin_mm: tuple[float, float, float]
    normal: tuple[float, float, float]
    extent_u_mm: float
    extent_v_mm: float


@dataclass(frozen=True)
class CylindricalFace:
    """Цилиндрическая грань — общий тип для сквозных отверстий И
    галтелей-скруглений кромок, различаемых по angular_extent_rad/
    is_full_turn (см. occ_feature_extract_script.py docstring — критерий
    подтверждён эмпирически на реальном fixture Кронштейн.STEP)."""

    radius_mm: float
    axis_origin_mm: tuple[float, float, float]
    axis_direction: tuple[float, float, float]
    angular_extent_rad: float
    is_full_turn: bool
    height_mm: float


@dataclass(frozen=True)
class PartTopology:
    """Полный сырой результат обхода B-rep — вход для классификатора фич,
    не для генератора тулпаса напрямую."""

    planar_faces: tuple[PlanarFace, ...] = field(default_factory=tuple)
    cylindrical_faces: tuple[CylindricalFace, ...] = field(default_factory=tuple)
    other_face_count: int = 0  # конусы/сплайны/тор и т.п. — не покрыты v1 (см. PLAN.md §2)
    total_face_count: int = 0
    bounding_box_mm: tuple[float, float, float, float, float, float] = (0, 0, 0, 0, 0, 0)


@dataclass(frozen=True)
class MillableFace:
    """Плоская грань, пригодная для торцевого/контурного фрезерования —
    подмножество planar_faces топологии после классификации."""

    z_height_mm: float
    normal_up: bool  # True — верхняя грань (обрабатывается сверху), False — нижняя/боковая


@dataclass(frozen=True)
class RecognizedHole:
    """Сквозное или глухое цилиндрическое отверстие — классифицировано
    из CylindricalFace по is_full_turn=True."""

    center_xy_mm: tuple[float, float]
    diameter_mm: float
    depth_mm: float
    through: bool


@dataclass(frozen=True)
class PartFeatureSet:
    """Результат классификации топологии в обрабатываемые фрезерованием
    фичи — то, что реально удалось распознать, плюс то, что не покрыто
    (для честного предупреждения вместо выдуманной траектории)."""

    millable_faces: tuple[MillableFace, ...] = field(default_factory=tuple)
    holes: tuple[RecognizedHole, ...] = field(default_factory=tuple)
    unrecognized_face_count: int = 0  # галтели/фаски/конусы/сплайны — не самостоятельные фичи v1
    total_face_count: int = 0
    is_supported: bool = True  # False — деталь преимущественно непризматическая, тулпас не строится

    @property
    def has_any_feature(self) -> bool:
        return len(self.millable_faces) > 0 or len(self.holes) > 0

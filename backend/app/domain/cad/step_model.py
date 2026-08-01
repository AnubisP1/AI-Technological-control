"""Доменные структуры результата разбора STEP-модели.

Не зависят от способа парсинга (regex или pythonocc-core) — это контракт
между domain и infrastructure (см. IStepParser в step_parser_port.py и
docs/ARCHITECTURE.md, раздел "STEP-парсинг").
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class BoundingBox:
    x_min: float
    x_max: float
    y_min: float
    y_max: float
    z_min: float
    z_max: float

    @property
    def length_x(self) -> float:
        return round(self.x_max - self.x_min, 3)

    @property
    def length_y(self) -> float:
        return round(self.y_max - self.y_min, 3)

    @property
    def length_z(self) -> float:
        return round(self.z_max - self.z_min, 3)


@dataclass(frozen=True)
class FaceColour:
    face_ref: int
    r: float
    g: float
    b: float


@dataclass(frozen=True)
class StepModel:
    """Результат разбора одного STEP-файла — то, с чем работает остальной
    домен (сверка с НСИ, классификация поверхностей), не зависимо от того,
    каким парсером получен результат."""

    file_path: str
    product_name: str
    software: str | None
    face_count: int
    bounding_box: BoundingBox | None
    face_colours: tuple[FaceColour, ...] = field(default_factory=tuple)

    @property
    def has_colour_annotations(self) -> bool:
        return len(self.face_colours) > 0

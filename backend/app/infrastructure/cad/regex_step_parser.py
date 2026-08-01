"""Regex-парсер STEP AP214 (ISO 10303-21) без зависимости от OpenCASCADE.

Baseline-реализация IStepParser (см. QUESTIONS.md №1: pythonocc-core на
Python 3.11 подключается позже как альтернативная реализация того же
порта, когда понадобится точный B-rep для UV-Net). Логика извлечения
цвета через цепочку STYLED_ITEM -> ... -> COLOUR_RGB опирается на подход
из Литература/НПО 2026/src/step_parser.py, переписана под доменный
контракт этого проекта и дополнена обработкой STEP-escape-последовательностей
\\X2\\...\\X0\\ (не-ASCII текст в кириллических STEP-файлах от C3D/АСКОН,
не совпадает по формату с файлами SolidWorks, под которые был написан
оригинальный парсер).
"""

from __future__ import annotations

import re
from pathlib import Path

from app.domain.cad.step_model import BoundingBox, FaceColour, StepModel

_RE_CARTESIAN = re.compile(
    r"CARTESIAN_POINT\s*\(\s*'[^']*'\s*,\s*\(\s*"
    r"([-\d.Ee+]+)\s*,\s*([-\d.Ee+]+)\s*,\s*([-\d.Ee+]+)\s*\)\s*\)"
)
_RE_COLOUR = re.compile(
    r"#(\d+)\s*=\s*COLOUR_RGB\s*\(\s*'[^']*'\s*,\s*"
    r"([\d.Ee+]+)\s*,\s*([\d.Ee+]+)\s*,\s*([\d.Ee+]+)\s*\)"
)
_RE_ADVANCED_FACE = re.compile(r"#(\d+)\s*=\s*ADVANCED_FACE\s*\(")
_RE_STYLED_ITEM_FULL = re.compile(
    r"#(\d+)\s*=\s*STYLED_ITEM\s*\(\s*'[^']*'\s*,\s*\(\s*#(\d+)\s*\)\s*,\s*#(\d+)\s*\)"
)
_RE_FILL_COLOUR = re.compile(r"#(\d+)\s*=\s*FILL_AREA_STYLE_COLOUR\s*\(\s*'[^']*'\s*,\s*#(\d+)\s*\)")
_RE_FILL_AREA = re.compile(r"#(\d+)\s*=\s*FILL_AREA_STYLE\s*\(\s*\$?\s*'?[^,]*'?\s*,\s*\(\s*#(\d+)\s*\)\s*\)")
_RE_SURFACE_STYLE_FILL = re.compile(r"#(\d+)\s*=\s*SURFACE_STYLE_FILL_AREA\s*\(\s*#(\d+)\s*\)")
_RE_SURFACE_SIDE = re.compile(r"#(\d+)\s*=\s*SURFACE_SIDE_STYLE\s*\(\s*'[^']*'\s*,\s*\(\s*#(\d+)\s*\)\s*\)")
_RE_SURFACE_STYLE_USAGE = re.compile(r"#(\d+)\s*=\s*SURFACE_STYLE_USAGE\s*\(\s*\.[A-Z]+\.\s*,\s*#(\d+)\s*\)")
_RE_PRESENTATION_STYLE = re.compile(r"#(\d+)\s*=\s*PRESENTATION_STYLE_ASSIGNMENT\s*\(\s*\(\s*#(\d+)\s*\)\s*\)")
_RE_FILE_NAME = re.compile(r"FILE_NAME\s*\(\s*'([^']*)'")
_RE_PRODUCT = re.compile(r"PRODUCT\s*\(\s*'[^']*'\s*,\s*'((?:[^'\\]|\\.)*)'")
_RE_SOFTWARE_HINT = re.compile(r"'(SolidWorks[^']*|C3D[^']*|КОМПАС[^']*|ASCON[^']*)'", re.IGNORECASE)
_RE_STEP_ESCAPE = re.compile(r"\\X2\\((?:[0-9A-Fa-f]{4})+)\\X0\\")


def _decode_step_unicode_escapes(text: str) -> str:
    """Раскодирует escape-последовательности ISO-10303-21 \\X2\\HHHH...\\X0\\
    (каждые 4 hex-символа — code point UCS-2) в обычные Unicode-символы.
    Используется кириллическими экспортами из C3D/АСКОН вместо прямого UTF-8."""

    def _replace(match: re.Match[str]) -> str:
        hex_blob = match.group(1)
        chars = [
            chr(int(hex_blob[i : i + 4], 16)) for i in range(0, len(hex_blob), 4)
        ]
        return "".join(chars)

    return _RE_STEP_ESCAPE.sub(_replace, text)


class RegexStepParser:
    """Baseline-реализация IStepParser на регулярных выражениях."""

    def parse(self, file_path: Path) -> StepModel:
        raw = file_path.read_bytes()
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            text = raw.decode("windows-1251", errors="replace")
        text = _decode_step_unicode_escapes(text)

        product_name = self._parse_product_name(text)
        software = self._parse_software(text)
        bounding_box = self._compute_bounding_box(text)
        face_count = len(_RE_ADVANCED_FACE.findall(text))
        face_colours = self._parse_face_colours(text)

        return StepModel(
            file_path=str(file_path),
            product_name=product_name,
            software=software,
            face_count=face_count,
            bounding_box=bounding_box,
            face_colours=tuple(face_colours),
        )

    def _parse_product_name(self, text: str) -> str:
        match = _RE_PRODUCT.search(text)
        return match.group(1) if match else ""

    def _parse_software(self, text: str) -> str | None:
        match = _RE_SOFTWARE_HINT.search(text)
        return match.group(1) if match else None

    def _compute_bounding_box(self, text: str) -> BoundingBox | None:
        points = _RE_CARTESIAN.findall(text)
        if not points:
            return None
        xs = [float(p[0]) for p in points]
        ys = [float(p[1]) for p in points]
        zs = [float(p[2]) for p in points]
        return BoundingBox(
            x_min=round(min(xs), 3), x_max=round(max(xs), 3),
            y_min=round(min(ys), 3), y_max=round(max(ys), 3),
            z_min=round(min(zs), 3), z_max=round(max(zs), 3),
        )

    def _parse_face_colours(self, text: str) -> list[FaceColour]:
        colours = {
            int(m.group(1)): (float(m.group(2)), float(m.group(3)), float(m.group(4)))
            for m in _RE_COLOUR.finditer(text)
        }
        if not colours:
            return []

        fill_colour_map = {int(m.group(1)): int(m.group(2)) for m in _RE_FILL_COLOUR.finditer(text)}
        fill_area_map = {int(m.group(1)): int(m.group(2)) for m in _RE_FILL_AREA.finditer(text)}
        surf_fill_map = {int(m.group(1)): int(m.group(2)) for m in _RE_SURFACE_STYLE_FILL.finditer(text)}
        surf_side_map = {int(m.group(1)): int(m.group(2)) for m in _RE_SURFACE_SIDE.finditer(text)}
        surf_usage_map = {int(m.group(1)): int(m.group(2)) for m in _RE_SURFACE_STYLE_USAGE.finditer(text)}
        pres_map = {int(m.group(1)): int(m.group(2)) for m in _RE_PRESENTATION_STYLE.finditer(text)}

        results: list[FaceColour] = []
        for match in _RE_STYLED_ITEM_FULL.finditer(text):
            pres_ref = int(match.group(2))
            face_ref = int(match.group(3))
            colour_ref = self._trace_colour(
                pres_ref, pres_map, surf_usage_map, surf_side_map,
                surf_fill_map, fill_area_map, fill_colour_map,
            )
            if colour_ref is not None and colour_ref in colours:
                r, g, b = colours[colour_ref]
                results.append(FaceColour(face_ref=face_ref, r=r, g=g, b=b))
        return results

    def _trace_colour(
        self, pres_ref: int, pres_map: dict, surf_usage_map: dict,
        surf_side_map: dict, surf_fill_map: dict, fill_area_map: dict,
        fill_colour_map: dict,
    ) -> int | None:
        chain = [pres_map, surf_usage_map, surf_side_map, surf_fill_map, fill_area_map, fill_colour_map]
        current = pres_ref
        for mapping in chain:
            current = mapping.get(current)
            if current is None:
                return None
        return current

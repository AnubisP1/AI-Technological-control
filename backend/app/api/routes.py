from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import APIRouter, UploadFile

from app.domain.cad.kd_analysis import KdAnalysisResult
from app.infrastructure.cad.auto_drawing_parser import AutoDrawingParser
from app.infrastructure.cad.auto_view_detector import AutoViewDetector
from app.infrastructure.cad.regex_step_parser import RegexStepParser
from app.infrastructure.resource_governor import configure as get_resource_limits
from app.services.kd_analysis_service import KdAnalysisService

router = APIRouter()

_kd_analysis_service = KdAnalysisService(
    drawing_parser=AutoDrawingParser(),
    view_detector=AutoViewDetector(),
    step_parser=RegexStepParser(),
)


@router.get("/health")
def health() -> dict:
    limits = get_resource_limits()
    return {
        "status": "ok",
        "cpu_thread_budget": limits.thread_count,
        "cpu_count_total": limits.cpu_count_total,
    }


def _result_to_dict(result: KdAnalysisResult) -> dict:
    drawing_json = None
    if result.drawing is not None:
        tb = result.drawing.title_block
        drawing_json = {
            "has_text_layer": result.drawing.has_text_layer,
            "title_block": {
                "designation": tb.designation,
                "part_name": tb.part_name,
                "material": tb.material,
                "blank_designation": tb.blank_designation,
                "scale": tb.scale,
                "sheet_format": tb.sheet_format,
                "mass": tb.mass,
            },
            "technical_requirements": [
                {"number": r.number, "text": r.text}
                for r in result.drawing.technical_requirements
            ],
        }

    view_detection_json = None
    if result.view_detection is not None:
        view_detection_json = {
            "method": result.view_detection.method,
            "view_count": result.view_detection.view_count,
            "regions": [
                {
                    "x0": region.x0, "y0": region.y0, "x1": region.x1, "y1": region.y1,
                    "element_count": region.element_count,
                }
                for region in result.view_detection.regions
            ],
        }

    step_json = None
    if result.step_model is not None:
        sm = result.step_model
        step_json = {
            "product_name": sm.product_name,
            "software": sm.software,
            "face_count": sm.face_count,
            "bounding_box": (
                {
                    "length_x": sm.bounding_box.length_x,
                    "length_y": sm.bounding_box.length_y,
                    "length_z": sm.bounding_box.length_z,
                }
                if sm.bounding_box
                else None
            ),
            "has_colour_annotations": sm.has_colour_annotations,
            "colour_count": len(sm.face_colours),
        }

    return {
        "is_complete": result.is_complete,
        "drawing": drawing_json,
        "view_detection": view_detection_json,
        "step_model": step_json,
    }


@router.post("/kd/analyze")
async def analyze_kd(
    drawing: UploadFile | None = None,
    step_model: UploadFile | None = None,
) -> dict:
    """Модуль 1.1: анализ загруженного комплекта КД (чертёж PDF + STEP-модель).

    Файлы сохраняются во временную директорию на время разбора и удаляются
    сразу после — не остаются на диске дольше запроса.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        drawing_path = None
        if drawing is not None:
            drawing_path = tmp_path / (drawing.filename or "drawing.pdf")
            drawing_path.write_bytes(await drawing.read())

        step_path = None
        if step_model is not None:
            step_path = tmp_path / (step_model.filename or "model.step")
            step_path.write_bytes(await step_model.read())

        result = await _kd_analysis_service.analyze(
            drawing_path=drawing_path, step_path=step_path
        )
        return _result_to_dict(result)

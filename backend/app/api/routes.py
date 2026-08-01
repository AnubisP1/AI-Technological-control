from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import Response

from app.domain.cad.kd_analysis import KdAnalysisResult
from app.domain.kd_review.review_model import KdReviewReport
from app.domain.manufacturing.approval_model import ApprovalDecision
from app.domain.manufacturing.simulation_model import SimulationPlan
from app.domain.process_planning.print_card_model import PostprocessingCard, PrintProcessCard
from app.domain.process_planning.route_card_model import RouteCard
from app.domain.quality_control.serial_production_model import QualityReport
from app.infrastructure.cad.auto_drawing_parser import AutoDrawingParser
from app.infrastructure.cad.auto_view_detector import AutoViewDetector
from app.infrastructure.cad.regex_step_parser import RegexStepParser
from app.infrastructure.config import get_settings
from app.infrastructure.db.nsi_db import NsiDatabase, build_database, connect
from app.infrastructure.db.sqlite_nsi_lookup import SqliteNsiLookup
from app.infrastructure.db.sqlite_print_planning_lookup import SqlitePrintPlanningLookup
from app.infrastructure.db.sqlite_process_planning_lookup import SqliteProcessPlanningLookup
from app.infrastructure.llm.yandex_gpt_text_generator import YandexGptTextGenerator
from app.infrastructure.quality_control.opencv_photo_comparator import OpenCvPhotoComparator
from app.infrastructure.resource_governor import configure as get_resource_limits
from app.infrastructure.worker_pool import run_heavy
from app.services.approval_service import ApprovalRejectionRequiresCommentError, ApprovalService
from app.services.kd_analysis_service import KdAnalysisService
from app.services.kd_review_pdf_export import generate_kd_review_pdf
from app.services.kd_review_service import KdReviewService
from app.services.manufacturing_simulation_service import ManufacturingSimulationService
from app.services.print_card_generator import PrintCardGenerator
from app.services.print_process_planning_service import PrintProcessPlanningService
from app.services.process_planning_service import ProcessPlanningService
from app.services.quality_control_service import QualityControlService
from app.services.route_card_generator import RouteCardGenerator, parse_layout_columns

router = APIRouter()
_approval_service = ApprovalService()
_simulation_service = ManufacturingSimulationService()
_quality_control_service = QualityControlService(OpenCvPhotoComparator())

_drawing_parser = AutoDrawingParser()

_kd_analysis_service = KdAnalysisService(
    drawing_parser=_drawing_parser,
    view_detector=AutoViewDetector(),
    step_parser=RegexStepParser(),
)


def _get_metal_db_path() -> Path:
    """Строит metal.sqlite при первом обращении, если файла ещё нет —
    сверка с НСИ (Модуль 1.2) не должна требовать ручного шага перед
    запуском backend."""
    settings = get_settings()
    db_path = settings.database_dir / "metal.sqlite"
    if not db_path.exists():
        build_database(NsiDatabase.METAL, db_path)
    return db_path


def _get_additive_db_path() -> Path:
    """Аналог _get_metal_db_path() для аддитивной НСИ (пластик)."""
    settings = get_settings()
    db_path = settings.database_dir / "additive.sqlite"
    if not db_path.exists():
        build_database(NsiDatabase.ADDITIVE, db_path)
    return db_path


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


def _review_to_dict(report: KdReviewReport) -> dict:
    material_json = None
    if report.material_check is not None:
        mc = report.material_check
        material_json = {
            "material_from_drawing": mc.material_from_drawing,
            "status": mc.status.value,
            "matched_grade": mc.matched_grade,
            "matched_gost": mc.matched_gost,
            "note": mc.note,
        }

    blank_json = None
    if report.blank_check is not None:
        bc = report.blank_check
        blank_json = {
            "blank_from_drawing": bc.blank_from_drawing,
            "status": bc.status.value,
            "matched_designation": bc.matched_designation,
            "note": bc.note,
        }

    return {
        "material_check": material_json,
        "blank_check": blank_json,
        "technical_requirement_checks": [
            {
                "number": tt.number,
                "text": tt.text,
                "is_recognized": tt.is_recognized,
                "category": tt.category,
            }
            for tt in report.technical_requirement_checks
        ],
        "findings": [
            {"severity": f.severity, "message": f.message} for f in report.findings
        ],
        "has_blocking_findings": report.has_blocking_findings,
        "summary": (
            {"text": report.summary.text, "generated_by": report.summary.generated_by}
            if report.summary is not None
            else None
        ),
    }


def _build_text_generator():
    """Возвращает YandexGptTextGenerator, если в .env заданы ключи
    (осознанное исключение из офлайн-требования, см. QUESTIONS.md №12),
    иначе None — тогда KdReviewService работает целиком офлайн на
    шаблонном тексте."""
    settings = get_settings()
    if not settings.yandex_gpt_api_key or not settings.yandex_gpt_folder_id:
        return None
    return YandexGptTextGenerator(
        api_key=settings.yandex_gpt_api_key, folder_id=settings.yandex_gpt_folder_id
    )


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


@router.post("/kd/review")
async def review_kd(drawing: UploadFile) -> dict:
    """Модуль 1.2: сверка чертежа с БД НСИ (материал, заготовка) и оценка
    технических требований — генерация отчёта об оценке КД.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        drawing_path = Path(tmp_dir) / (drawing.filename or "drawing.pdf")
        drawing_path.write_bytes(await drawing.read())

        drawing_model = await run_heavy(_drawing_parser.parse, drawing_path)

    metal_db_path = _get_metal_db_path()
    review_service = KdReviewService(
        nsi_lookup=SqliteNsiLookup(metal_db_path), text_generator=_build_text_generator()
    )
    report = review_service.review(drawing_model)
    return _review_to_dict(report)


@router.post("/kd/review/pdf")
async def review_kd_pdf(drawing: UploadFile) -> Response:
    """Экспорт отчёта Модуля 1.2 в PDF (Фаза 8, см. dev/QUESTIONS.md №12)
    — та же сверка, что и /kd/review, но результат отдаётся файлом.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        drawing_path = Path(tmp_dir) / (drawing.filename or "drawing.pdf")
        drawing_path.write_bytes(await drawing.read())

        drawing_model = await run_heavy(_drawing_parser.parse, drawing_path)

    metal_db_path = _get_metal_db_path()
    review_service = KdReviewService(
        nsi_lookup=SqliteNsiLookup(metal_db_path), text_generator=_build_text_generator()
    )
    report = review_service.review(drawing_model)

    part_name = drawing_model.title_block.part_name if drawing_model else None
    pdf_bytes = await run_heavy(generate_kd_review_pdf, report, part_name=part_name)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="kd_review_report.pdf"'},
    )


def _route_card_to_dict(card: RouteCard, warnings: tuple[str, ...]) -> dict:
    return {
        "part_name": card.part_name,
        "material_grade": card.material_grade,
        "gost_form": card.gost_form,
        "columns": list(card.columns),
        "rows": [list(row.values) for row in card.rows],
        "warnings": list(warnings),
    }


@router.post("/kd/route-card")
async def generate_route_card(drawing: UploadFile) -> dict:
    """Модуль 1.3 (упрощённый автоподбор, см. dev/PLAN.md Фаза 4):
    разбирает чертёж, подбирает станки/операции по правилам совместимости
    из БД НСИ и генерирует маршрутную карту по шаблону document_template.

    Автоподбор не рассчитывает нормы времени и не назначает цех/разряд —
    соответствующие графы карты остаются пустыми, не выдуманными.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        drawing_path = Path(tmp_dir) / (drawing.filename or "drawing.pdf")
        drawing_path.write_bytes(await drawing.read())

        drawing_model = await run_heavy(_drawing_parser.parse, drawing_path)

    metal_db_path = _get_metal_db_path()
    planning_service = ProcessPlanningService(SqliteProcessPlanningLookup(metal_db_path))
    planning_result = planning_service.plan(
        part_name=drawing_model.title_block.part_name if drawing_model else None,
        material_grade=drawing_model.title_block.material if drawing_model else None,
    )

    connection = connect(metal_db_path)
    try:
        template_row = connection.execute(
            "SELECT gost_form, layout_schema FROM document_template WHERE code = 'MK'"
        ).fetchone()
    finally:
        connection.close()

    columns = parse_layout_columns(template_row["layout_schema"]) if template_row else ()
    gost_form = template_row["gost_form"] if template_row else None

    route_card = RouteCardGenerator().generate(
        planning_result, columns=columns, gost_form=gost_form
    )
    return _route_card_to_dict(route_card, planning_result.warnings)


def _print_process_card_to_dict(card: PrintProcessCard) -> dict:
    return {
        "part_name": card.part_name,
        "columns": list(card.columns),
        "row": list(card.row.values),
    }


def _postprocessing_card_to_dict(card: PostprocessingCard) -> dict:
    return {
        "columns": list(card.columns),
        "rows": [list(row.values) for row in card.rows],
    }


@router.post("/print/route-card")
async def generate_print_route_card(
    step_model: UploadFile,
    am_technology_code: str,
    material_group_code: str,
) -> dict:
    """Модуль 1.3 для пластиковых изделий (упрощённый автоподбор,
    аддитивные технологии). В отличие от металла, на вход по ТЗ подаётся
    только STEP-модель без чертежа — материал и технология печати не
    извлекаются из документа, а указываются пользователем явно
    (am_technology_code, напр. 'FDM'/'SLA'; material_group_code, напр.
    'PETG'/'RESIN_STD').

    Подбирает принтер и цепочку постобработки по правилам совместимости
    additive-НСИ, генерирует карту техпроцесса печати и карту
    постобработки по шаблонам am_document_template. Параметры печати
    (высота слоя, время, расход материала) не рассчитываются — графы
    остаются пустыми, не выдуманными.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        step_path = Path(tmp_dir) / (step_model.filename or "model.step")
        step_path.write_bytes(await step_model.read())

        step = await run_heavy(RegexStepParser().parse, step_path)

    additive_db_path = _get_additive_db_path()
    planning_service = PrintProcessPlanningService(SqlitePrintPlanningLookup(additive_db_path))
    planning_result = planning_service.plan(
        part_name=step.product_name or None,
        am_technology_code=am_technology_code,
        material_group_code=material_group_code,
    )

    connection = connect(additive_db_path)
    try:
        process_template = connection.execute(
            "SELECT layout_schema FROM am_document_template WHERE code = 'PRINT_CARD'"
        ).fetchone()
        pp_template = connection.execute(
            "SELECT layout_schema FROM am_document_template WHERE code = 'PP_CARD'"
        ).fetchone()
    finally:
        connection.close()

    process_columns = (
        parse_layout_columns(process_template["layout_schema"]) if process_template else ()
    )
    pp_columns = parse_layout_columns(pp_template["layout_schema"]) if pp_template else ()

    generator = PrintCardGenerator()
    process_card = generator.generate_process_card(planning_result, columns=process_columns)
    postprocessing_card = generator.generate_postprocessing_card(
        planning_result, columns=pp_columns
    )

    return {
        "process_card": _print_process_card_to_dict(process_card),
        "postprocessing_card": _postprocessing_card_to_dict(postprocessing_card),
        "warnings": list(planning_result.warnings),
    }


@router.post("/manufacturing/approval")
async def decide_approval(decision: str, comment: str | None = None) -> dict:
    """Модуль 2, шаг 1: согласование комплекта ТД главным технологом.

    Решение не сохраняется — при 'rejected' пользователь возвращается в
    Модуль 1 для повторной генерации с учётом комментария; при
    'approved' фронтенд переходит к симуляции изготовления.
    """
    try:
        parsed_decision = ApprovalDecision(decision)
    except ValueError as exc:
        raise HTTPException(
            status_code=422, detail=f"Неизвестное решение '{decision}' — ожидается approved/rejected"
        ) from exc

    try:
        result = _approval_service.decide(decision=parsed_decision, comment=comment)
    except ApprovalRejectionRequiresCommentError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return {
        "decision": result.decision.value,
        "comment": result.comment,
        "can_start_simulation": result.can_start_simulation,
    }


def _simulation_plan_to_dict(plan: SimulationPlan) -> dict:
    return {
        "part_name": plan.part_name,
        "material_kind": plan.material_kind,
        "total_seconds": plan.total_seconds,
        "operations": [
            {
                "sequence_no": op.sequence_no,
                "name": op.name,
                "machine_icon": op.machine_icon,
                "machine_label": op.machine_label,
                "program_lines": list(op.program_lines),
                "duration_share": op.duration_share,
            }
            for op in plan.operations
        ],
    }


@router.post("/manufacturing/simulate/metal")
async def simulate_metal_manufacturing(drawing: UploadFile) -> dict:
    """Модуль 2, шаг 2 (металл): строит план симуляции изготовления из
    того же автоподбора техпроцесса, что и /kd/route-card — эндпоинт не
    выполняет собственный подбор оборудования заново.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        drawing_path = Path(tmp_dir) / (drawing.filename or "drawing.pdf")
        drawing_path.write_bytes(await drawing.read())

        drawing_model = await run_heavy(_drawing_parser.parse, drawing_path)

    metal_db_path = _get_metal_db_path()
    planning_service = ProcessPlanningService(SqliteProcessPlanningLookup(metal_db_path))
    planning_result = planning_service.plan(
        part_name=drawing_model.title_block.part_name if drawing_model else None,
        material_grade=drawing_model.title_block.material if drawing_model else None,
    )

    plan = _simulation_service.build_metal_plan(planning_result)
    return {
        "plan": _simulation_plan_to_dict(plan),
        "warnings": list(planning_result.warnings),
    }


@router.post("/manufacturing/simulate/print")
async def simulate_print_manufacturing(
    step_model: UploadFile,
    am_technology_code: str,
    material_group_code: str,
) -> dict:
    """Модуль 2, шаг 2 (пластик): аналог simulate_metal_manufacturing на
    основе автоподбора печати из /print/route-card."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        step_path = Path(tmp_dir) / (step_model.filename or "model.step")
        step_path.write_bytes(await step_model.read())

        step = await run_heavy(RegexStepParser().parse, step_path)

    additive_db_path = _get_additive_db_path()
    planning_service = PrintProcessPlanningService(SqlitePrintPlanningLookup(additive_db_path))
    planning_result = planning_service.plan(
        part_name=step.product_name or None,
        am_technology_code=am_technology_code,
        material_group_code=material_group_code,
    )

    plan = _simulation_service.build_print_plan(planning_result)
    return {
        "plan": _simulation_plan_to_dict(plan),
        "warnings": list(planning_result.warnings),
    }


def _quality_report_to_dict(report: QualityReport) -> dict:
    plan_json = None
    if report.serial_production_plan is not None:
        p = report.serial_production_plan
        plan_json = {
            "operation_count": p.operation_count,
            "estimated_cycle_time_minutes": p.estimated_cycle_time_minutes,
            "estimated_batch_100_duration_days": p.estimated_batch_100_duration_days,
            "estimated_unit_cost_rub": p.estimated_unit_cost_rub,
            "risk_level": p.risk_level,
            "estimated_defect_rate_percent": p.estimated_defect_rate_percent,
            "workshop_load_notes": list(p.workshop_load_notes),
            "is_demonstration_estimate": p.is_demonstration_estimate,
        }

    return {
        "verdict": report.verdict,
        "similarity_score": report.similarity_score,
        "notes": list(report.notes),
        "serial_production_plan": plan_json,
        "optimization_suggestions": [s.text for s in report.optimization_suggestions],
        "remediation_recommendations": [r.text for r in report.remediation_recommendations],
    }


@router.post("/quality/assess/metal")
async def assess_quality_metal(
    drawing: UploadFile, reference_photo: UploadFile, actual_photo: UploadFile
) -> dict:
    """Модуль 3 (металл): сравнивает фото изготовленной детали с
    эталонным фото (см. dev/QUESTIONS.md — рендер реальной геометрии
    STEP недоступен без pythonocc-core, поэтому эталон — фото, а не
    рендер 3D-модели), затем ветвится в документы для серии (норма) или
    рекомендации по устранению брака.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        drawing_path = tmp_path / (drawing.filename or "drawing.pdf")
        drawing_path.write_bytes(await drawing.read())
        reference_path = tmp_path / (reference_photo.filename or "reference.jpg")
        reference_path.write_bytes(await reference_photo.read())
        actual_path = tmp_path / (actual_photo.filename or "actual.jpg")
        actual_path.write_bytes(await actual_photo.read())

        drawing_model = await run_heavy(_drawing_parser.parse, drawing_path)

        metal_db_path = _get_metal_db_path()
        planning_service = ProcessPlanningService(SqliteProcessPlanningLookup(metal_db_path))
        planning_result = planning_service.plan(
            part_name=drawing_model.title_block.part_name if drawing_model else None,
            material_grade=drawing_model.title_block.material if drawing_model else None,
        )
        simulation_plan = _simulation_service.build_metal_plan(planning_result)

        report = await run_heavy(
            _quality_control_service.assess,
            reference_photo_path=reference_path,
            actual_photo_path=actual_path,
            simulation_plan=simulation_plan,
            planning_warnings=planning_result.warnings,
        )
    return _quality_report_to_dict(report)


@router.post("/quality/assess/print")
async def assess_quality_print(
    step_model: UploadFile,
    reference_photo: UploadFile,
    actual_photo: UploadFile,
    am_technology_code: str,
    material_group_code: str,
) -> dict:
    """Модуль 3 (пластик) — аналог assess_quality_metal на основе
    автоподбора печати."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        step_path = tmp_path / (step_model.filename or "model.step")
        step_path.write_bytes(await step_model.read())
        reference_path = tmp_path / (reference_photo.filename or "reference.jpg")
        reference_path.write_bytes(await reference_photo.read())
        actual_path = tmp_path / (actual_photo.filename or "actual.jpg")
        actual_path.write_bytes(await actual_photo.read())

        step = await run_heavy(RegexStepParser().parse, step_path)

        additive_db_path = _get_additive_db_path()
        planning_service = PrintProcessPlanningService(SqlitePrintPlanningLookup(additive_db_path))
        planning_result = planning_service.plan(
            part_name=step.product_name or None,
            am_technology_code=am_technology_code,
            material_group_code=material_group_code,
        )
        simulation_plan = _simulation_service.build_print_plan(planning_result)

        report = await run_heavy(
            _quality_control_service.assess,
            reference_photo_path=reference_path,
            actual_photo_path=actual_path,
            simulation_plan=simulation_plan,
            planning_warnings=planning_result.warnings,
        )
    return _quality_report_to_dict(report)

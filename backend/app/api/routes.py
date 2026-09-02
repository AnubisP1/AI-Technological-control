from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel

from app.domain.cad.kd_analysis import KdAnalysisResult
from app.domain.kd_review.review_model import KdReviewReport
from app.domain.manufacturing.approval_model import ApprovalDecision
from app.domain.manufacturing.simulation_model import SimulationPlan
from app.domain.process_planning.material_recommendation_model import (
    MaterialRecommendationResult,
)
from app.domain.process_planning.print_card_model import PostprocessingCard, PrintProcessCard
from app.domain.process_planning.route_card_model import RouteCard
from app.domain.quality_control.serial_production_model import QualityReport
from app.infrastructure.cad.auto_drawing_parser import AutoDrawingParser
from app.infrastructure.cad.auto_view_detector import AutoViewDetector
from app.infrastructure.cad.regex_step_parser import RegexStepParser
from app.infrastructure.cad.step_mesh_exporter import export_step_to_stl
from app.infrastructure.config import get_settings
from app.infrastructure.db.nsi_db import NsiDatabase, build_database, connect
from app.infrastructure.db.sqlite_nsi_lookup import SqliteNsiLookup
from app.infrastructure.db.sqlite_print_planning_lookup import SqlitePrintPlanningLookup
from app.infrastructure.db.sqlite_process_planning_lookup import SqliteProcessPlanningLookup
from app.infrastructure.llm.chained_chat_responder import ChainedChatResponder
from app.infrastructure.llm.chained_text_generator import ChainedTextGenerator
from app.infrastructure.llm.qwen_chat_responder import QwenChatResponder
from app.infrastructure.llm.qwen_text_generator import QwenTextGenerator
from app.infrastructure.quality_control.opencv_photo_comparator import OpenCvPhotoComparator
from app.infrastructure.resource_governor import configure as get_resource_limits
from app.infrastructure.worker_pool import run_heavy
from app.services.approval_service import ApprovalRejectionRequiresCommentError, ApprovalService
from app.services.assistant_service import AssistantService
from app.services.kd_analysis_service import KdAnalysisService
from app.services.kd_review_pdf_export import generate_kd_review_pdf
from app.services.kd_review_service import KdReviewService
from app.services.manufacturing_simulation_service import ManufacturingSimulationService
from app.services.material_recommendation_service import MaterialRecommendationService
from app.services.nsi_browser_service import NsiBrowserService
from app.services.operation_card_generator import OperationCardGenerator
from app.services.operation_card_pdf_export import generate_operation_card_pdf
from app.services.print_card_generator import PrintCardGenerator
from app.services.print_card_pdf_export import generate_print_card_pdf
from app.services.print_process_planning_service import PrintProcessPlanningService
from app.services.process_planning_service import ProcessPlanningService
from app.services.quality_control_service import QualityControlService
from app.services.route_card_generator import RouteCardGenerator, parse_layout_columns
from app.services.route_card_pdf_export import generate_route_card_pdf
from app.services.toolpath_pipeline import ToolpathPipelineResult, run_toolpath_pipeline

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


def _get_nsi_browser_service() -> NsiBrowserService:
    return NsiBrowserService(_get_metal_db_path(), _get_additive_db_path())


@router.get("/nsi/{database}/tables")
async def list_nsi_tables(database: str) -> list[dict]:
    """Просмотрщик БД НСИ целиком (Фаза 17, часть 5) — список таблиц с
    числом строк, без привязки к загруженной детали (в отличие от
    /kd/review, сверяющего конкретную деталь). database: 'metal' | 'additive'."""
    try:
        db = NsiDatabase(database)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Неизвестная база '{database}' — ожидается metal/additive")
    tables = _get_nsi_browser_service().list_tables(db)
    return [{"name": t.name, "row_count": t.row_count} for t in tables]


@router.get("/nsi/{database}/tables/{table_name}")
async def get_nsi_table_content(database: str, table_name: str) -> dict:
    try:
        db = NsiDatabase(database)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Неизвестная база '{database}' — ожидается metal/additive")
    content = _get_nsi_browser_service().table_content(db, table_name)
    if content is None:
        raise HTTPException(status_code=404, detail=f"Таблица '{table_name}' не найдена в базе '{database}'")
    return {
        "name": content.name,
        "columns": list(content.columns),
        "rows": [list(row) for row in content.rows],
        "total_row_count": content.total_row_count,
        "truncated": content.truncated,
    }


class ChatQuestion(BaseModel):
    question: str


def _get_assistant_service() -> AssistantService:
    return AssistantService(
        _get_metal_db_path(),
        _get_additive_db_path(),
        chat_responder=_build_chat_responder(),
        web_search_responder=_build_web_search_responder(),
    )


@router.post("/assistant/chat")
async def ask_assistant(body: ChatQuestion) -> dict:
    """AI-ассистент по вопросам НСИ/технологичности (Фаза 17, часть 5,
    экран "Обзор") — keyword-поиск по справочникам НСИ + LLM/шаблонный
    fallback (см. AssistantService). Через run_heavy — см. review_kd."""
    reply = await run_heavy(_get_assistant_service().ask, body.question)
    return {"text": reply.text, "generated_by": reply.generated_by}


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


def _build_chat_responder():
    """Собирает цепочку LLM-провайдеров по приоритету. В локальной
    (offline) сборке облачные провайдеры отсутствуют: доступен только
    локальный Qwen (если задан путь к модели). Если он не настроен —
    возвращает None, и AssistantService отвечает целиком офлайн
    шаблонным перечислением найденных фактов. Существование файла
    локальной модели не проверяется здесь заранее (дорого на каждый
    запрос) — LlamaCppEngine проверяет его при первой реальной загрузке
    и поднимает LlamaModelUnavailableError, которую ChainedChatResponder
    ловит и переходит к следующему провайдеру."""
    settings = get_settings()
    providers = []
    if settings.llama_model_path is not None:
        providers.append(
            QwenChatResponder(
                model_path=settings.llama_model_path, context_size=settings.llama_context_size
            )
        )
    if not providers:
        return None
    return ChainedChatResponder(tuple(providers))


def _build_web_search_responder():
    """В локальной (offline) сборке веб-поиск недоступен по определению:
    он требует обращения в интернет, что запрещено в этом контуре.
    Всегда возвращает None — AssistantService при отсутствии совпадений
    в НСИ честно сообщает, что данных нет, вместо обращения наружу."""
    return None


def _build_text_generator():
    """Аналог _build_chat_responder() для KdReviewService — та же
    цепочка приоритетов (локальный Qwen -> None/шаблон)."""
    settings = get_settings()
    providers = []
    if settings.llama_model_path is not None:
        providers.append(
            QwenTextGenerator(
                model_path=settings.llama_model_path, context_size=settings.llama_context_size
            )
        )
    if not providers:
        return None
    return ChainedTextGenerator(tuple(providers))


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


@router.post("/kd/step-mesh")
async def export_step_mesh(step_model: UploadFile) -> Response:
    """Реальная тесселяция STEP -> STL (Фаза 17, часть 5) — по прямому
    запросу пользователя заменяет параметрический прокси-бокс PartViewer
    настоящей геометрией детали, где это технически доступно.

    Требует внешнего conda-окружения с pythonocc-core (см.
    step_mesh_exporter.py, Settings.pythonocc_python_path) — если оно не
    настроено или экспорт не удался, отвечает 404 (не 500 — отсутствие
    точной геометрии не ошибка сервера, а ожидаемый fallback-путь),
    фронтенд в этом случае продолжает показывать прокси-бокс.
    """
    settings = get_settings()
    with tempfile.TemporaryDirectory() as tmp_dir:
        step_path = Path(tmp_dir) / (step_model.filename or "model.step")
        step_path.write_bytes(await step_model.read())

        stl_bytes = await run_heavy(
            export_step_to_stl, step_path, settings.pythonocc_python_path
        )

    if stl_bytes is None:
        raise HTTPException(
            status_code=404,
            detail="Реальная тесселяция недоступна (pythonocc-core не настроен или экспорт не удался)",
        )

    return Response(content=stl_bytes, media_type="model/stl")


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
    # Через run_heavy: с локальным Qwen (Фаза 18) _summarize() может
    # выполнять несколько секунд чистого CPU-инференса — блокировать им
    # event loop недопустимо (см. worker_pool.py).
    report = await run_heavy(review_service.review, drawing_model)
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
    report = await run_heavy(review_service.review, drawing_model)

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
        "technical_requirements": list(card.technical_requirements),
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
        blank_designation=drawing_model.title_block.blank_designation if drawing_model else None,
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


@router.post("/kd/route-card/pdf")
async def generate_route_card_pdf_endpoint(drawing: UploadFile) -> Response:
    """Экспорт маршрутной карты (см. /kd/route-card) в PDF по форме
    ГОСТ 3.1118-82 — реальная табличная сетка (Фаза 17), не текстовый
    список."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        drawing_path = Path(tmp_dir) / (drawing.filename or "drawing.pdf")
        drawing_path.write_bytes(await drawing.read())

        drawing_model = await run_heavy(_drawing_parser.parse, drawing_path)

    metal_db_path = _get_metal_db_path()
    planning_service = ProcessPlanningService(SqliteProcessPlanningLookup(metal_db_path))
    planning_result = planning_service.plan(
        part_name=drawing_model.title_block.part_name if drawing_model else None,
        material_grade=drawing_model.title_block.material if drawing_model else None,
        blank_designation=drawing_model.title_block.blank_designation if drawing_model else None,
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

    route_card = RouteCardGenerator().generate(planning_result, columns=columns, gost_form=gost_form)
    pdf_bytes = await run_heavy(generate_route_card_pdf, route_card)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="route_card.pdf"'},
    )


@router.post("/kd/operation-card/pdf")
async def generate_operation_card_pdf_endpoint(drawing: UploadFile) -> Response:
    """Экспорт операционной карты по форме ГОСТ 3.1404-86 — с
    рассчитанными режимами резания t/S/V/n (Фаза 17, CuttingModeCalculator),
    где расчёт был возможен (см. app/services/cutting_mode_calculator.py)."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        drawing_path = Path(tmp_dir) / (drawing.filename or "drawing.pdf")
        drawing_path.write_bytes(await drawing.read())

        drawing_model = await run_heavy(_drawing_parser.parse, drawing_path)

    metal_db_path = _get_metal_db_path()
    planning_service = ProcessPlanningService(SqliteProcessPlanningLookup(metal_db_path))
    planning_result = planning_service.plan(
        part_name=drawing_model.title_block.part_name if drawing_model else None,
        material_grade=drawing_model.title_block.material if drawing_model else None,
        blank_designation=drawing_model.title_block.blank_designation if drawing_model else None,
    )

    connection = connect(metal_db_path)
    try:
        template_row = connection.execute(
            "SELECT gost_form, layout_schema FROM document_template WHERE code = 'OK'"
        ).fetchone()
    finally:
        connection.close()

    columns = parse_layout_columns(template_row["layout_schema"]) if template_row else ()
    gost_form = template_row["gost_form"] if template_row else None

    operation_card = OperationCardGenerator().generate(
        planning_result, columns=columns, gost_form=gost_form
    )
    pdf_bytes = await run_heavy(generate_operation_card_pdf, operation_card)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="operation_card.pdf"'},
    )


def _print_process_card_to_dict(card: PrintProcessCard) -> dict:
    qs = card.quality_standard
    return {
        "part_name": card.part_name,
        "columns": list(card.columns),
        "row": list(card.row.values),
        "quality_standard": (
            {
                "tolerance_mm": qs.tolerance_mm,
                "min_wall_thickness_mm": qs.min_wall_thickness_mm,
                "roughness_ra_raw_um": qs.roughness_ra_raw_um,
                "roughness_ra_finished_um": qs.roughness_ra_finished_um,
                "min_thread_pitch_mm": qs.min_thread_pitch_mm,
                "assembly_clearance_mm": qs.assembly_clearance_mm,
                "source_note": qs.source_note,
            }
            if qs
            else None
        ),
        "print_estimate_note": card.print_estimate_note,
    }


def _postprocessing_card_to_dict(card: PostprocessingCard) -> dict:
    return {
        "columns": list(card.columns),
        "rows": [list(row.values) for row in card.rows],
    }


def _material_recommendation_result_to_dict(result: MaterialRecommendationResult) -> dict:
    return {
        "part_application_class_code": result.part_application_class_code,
        "matched_operating_conditions": list(result.matched_operating_conditions),
        "options": [
            {
                "priority": option.priority,
                "am_technology_code": option.am_technology_code,
                "am_technology_name": option.am_technology_name,
                "material_group_code": option.material_group_code,
                "material_group_name": option.material_group_name,
                "rationale": option.rationale,
                "source_type": option.source_type,
                "source_title": option.source_title,
                "source_reliability": option.source_reliability,
                "min_infill_percent": option.min_infill_percent,
                "recommended_wall_count": option.recommended_wall_count,
                "orientation_note": option.orientation_note,
            }
            for option in result.options
        ],
        "warnings": list(result.warnings),
    }


@router.get("/print/part-application-classes")
async def list_part_application_classes() -> list[dict]:
    """Справочник классов применения детали (БПЛА-домен: носовой обтекатель,
    крыло, винт и т.д., см. am_part.part_application_class) — источник
    выбора для автоподбора материала (Фаза 10), не для ручного выбора
    технологии/материала печати."""
    lookup = SqlitePrintPlanningLookup(_get_additive_db_path())
    classes = lookup.find_part_application_classes()
    return [
        {"code": c.code, "name": c.name, "description": c.description} for c in classes
    ]


@router.get("/print/operating-conditions")
async def list_operating_conditions(part_application_class_code: str | None = None) -> list[dict]:
    """Условия эксплуатации (температура/скорость потока/УФ/вибрация/удар/
    влажность). Без параметра — весь справочник; с параметром — только
    типичные для указанного класса детали (part_application_class_typical_condition),
    чтобы UI мог подсказать релевантный набор, не весь список целиком."""
    lookup = SqlitePrintPlanningLookup(_get_additive_db_path())
    part_class_id = None
    if part_application_class_code is not None:
        part_class = lookup.find_part_application_class_by_code(part_application_class_code)
        if part_class is None:
            raise HTTPException(
                status_code=404,
                detail=f"Класс применения детали '{part_application_class_code}' не найден",
            )
        part_class_id = part_class.id
    conditions = lookup.find_operating_conditions(part_class_id)
    return [
        {
            "code": c.code,
            "name": c.name,
            "condition_type": c.condition_type,
            "range_min": c.range_min,
            "range_max": c.range_max,
            "unit": c.unit,
        }
        for c in conditions
    ]


@router.post("/print/material-recommendations")
async def recommend_materials(
    part_application_class_code: str,
    operating_condition_codes: list[str] = Query(default=[]),
) -> dict:
    """Автоподбор материала/технологии печати по классу применения детали
    и условиям эксплуатации (Модуль 1.3, Фаза 10) — заменяет ручной выбор
    технологии/материала для пластика. Результат — упорядоченный по
    priority список вариантов с обоснованием и явной пометкой надёжности
    источника (source_type/source_reliability), не выдаётся за
    производственный расчёт. Не меняет /print/route-card и другие уже
    существующие эндпоинты — фронтенд берёт options[0] и передаёт его коды
    в них, как и раньше.
    """
    lookup = SqlitePrintPlanningLookup(_get_additive_db_path())
    service = MaterialRecommendationService(lookup)
    result = service.recommend(
        part_application_class_code=part_application_class_code,
        operating_condition_codes=tuple(operating_condition_codes),
    )
    return _material_recommendation_result_to_dict(result)


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
    (высота слоя, время, расход материала) рассчитываются по геометрии
    STEP (см. PrintParameterCalculator), заполнение (infill %) —
    справочное значение конкретной рекомендации автоподбора, не
    пересчитывается здесь. Технологические параметры конкретной марки
    материала (температура сопла/стола, требования к камере/хранению) —
    в material_print_profile, для экспертизы НСИ по пластику (Фаза 20).
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
        bounding_box=step.bounding_box,
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

    profile = planning_result.material_print_profile
    return {
        "process_card": _print_process_card_to_dict(process_card),
        "postprocessing_card": _postprocessing_card_to_dict(postprocessing_card),
        "warnings": list(planning_result.warnings),
        "material_print_profile": (
            {
                "trade_name": profile.trade_name,
                "print_temp_min_c": profile.print_temp_min_c,
                "print_temp_max_c": profile.print_temp_max_c,
                "bed_temp_c": profile.bed_temp_c,
                "requires_heated_chamber": profile.requires_heated_chamber,
                "requires_dry_storage": profile.requires_dry_storage,
            }
            if profile
            else None
        ),
    }


@router.post("/print/route-card/pdf")
async def generate_print_route_card_pdf_endpoint(
    step_model: UploadFile,
    am_technology_code: str,
    material_group_code: str,
) -> Response:
    """Экспорт карты техпроцесса печати + карты постобработки (см.
    /print/route-card) в PDF — свободная табличная форма (аддитивное
    производство не имеет отраслевого ГОСТ-бланка), с рассчитанными
    высотой слоя/временем печати/расходом материала (Фаза 17,
    PrintParameterCalculator), где расчёт был возможен."""
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
        bounding_box=step.bounding_box,
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
    postprocessing_card = generator.generate_postprocessing_card(planning_result, columns=pp_columns)

    pdf_bytes = await run_heavy(generate_print_card_pdf, process_card, postprocessing_card)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="print_process_card.pdf"'},
    )


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
    """Модуль 2, шаг 2 (металл), LEGACY-путь без геометрии: строит план
    статичной UI-симуляции (program_templates.py, одинаковый текст
    программы для любой детали данного типа операции) из того же
    автоподбора техпроцесса, что и /kd/route-card. Используется только
    для деталей БЕЗ загруженной STEP-модели — при наличии STEP фронтенд
    вызывает /manufacturing/toolpath/metal (Фаза 22, реальный тулпас по
    геометрии), а не этот эндпоинт.
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
        blank_designation=drawing_model.title_block.blank_designation if drawing_model else None,
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
        bounding_box=step.bounding_box,
    )

    plan = _simulation_service.build_print_plan(planning_result)
    return {
        "plan": _simulation_plan_to_dict(plan),
        "warnings": list(planning_result.warnings),
    }


def _toolpath_pipeline_result_to_dict(result: ToolpathPipelineResult) -> dict:
    toolpath = result.toolpath

    # Границы шагов voxel-симуляции по операциям — считается тем же
    # правилом, что material_removal_simulator.simulate_material_removal
    # использует для инкремента step (один шаг на каждый не-rapid move,
    # последовательно по всем операциям плана) — не отдельный источник
    # истины, а зеркало того же подсчёта, чтобы фронтенд мог подсветить
    # активную операцию синхронно с прогрессом voxel-анимации без
    # передачи полного списка moves (которые не сериализуются отдельно).
    step_cursor = 0
    operations_dicts = []
    for op in toolpath.operations:
        non_rapid_moves = sum(1 for m in op.moves if m.kind != "rapid")
        start_step = step_cursor
        step_cursor += non_rapid_moves
        operations_dicts.append(
            {
                "sequence_no": op.sequence_no,
                "feature_kind": op.feature_kind,
                "tool_diameter_mm": op.tool_diameter_mm,
                "tool_designation": op.tool_designation,
                "spindle_speed_rpm": op.spindle_speed_rpm,
                "feed_mm_min": op.feed_mm_min,
                "gcode_lines": list(op.gcode_lines),
                "estimated_time_min": op.estimated_time_min,
                "source_note": op.source_note,
                "start_step": start_step,
                "end_step": step_cursor,
                # Реальные координаты движения инструмента — нужны фронтенду
                # для анимации положения фрезы синхронно с voxel-съёмом
                # (см. ToolpathViewer.tsx), не только для текстового G-code.
                "moves": [
                    {"kind": m.kind, "x_mm": m.x_mm, "y_mm": m.y_mm, "z_mm": m.z_mm}
                    for m in op.moves
                ],
            }
        )

    toolpath_dict = {
        "part_name": toolpath.part_name,
        "stock_bounding_box_mm": list(toolpath.stock_bounding_box_mm),
        "unsupported_warning": toolpath.unsupported_warning,
        "warnings": list(toolpath.warnings),
        "operations": operations_dicts,
    }

    simulation_dict = None
    if result.simulation is not None:
        sim = result.simulation
        simulation_dict = {
            "grid": {
                "origin_mm": list(sim.grid.origin_mm),
                "voxel_size_mm": sim.grid.voxel_size_mm,
                "dims": list(sim.grid.dims),
            },
            "total_steps": sim.total_steps,
            # Компактный формат [x, y, z, шаг] вместо объектов с ключами —
            # существенно меньше JSON-payload при десятках тысяч событий
            # (см. историю разработки Фазы 22: ~1.25МБ объектами против
            # ~0.59МБ этим форматом на реальном fixture Кронштейн.STEP).
            "events": [[e.voxel_x, e.voxel_y, e.voxel_z, e.removed_at_step] for e in sim.events],
        }

    return {"toolpath": toolpath_dict, "simulation": simulation_dict}


@router.post("/manufacturing/toolpath/metal")
async def generate_metal_toolpath(step_model: UploadFile, drawing: UploadFile) -> dict:
    """Модуль 2, шаг 2 (металл), реальный путь (Фаза 22, dev/PLAN.md):
    строит фактический 3-осевой фрезерный тулпас по распознанной
    топологии STEP-модели (не статичный шаблон program_templates.py) —
    режимы резания из НСИ, реальные координаты движения инструмента,
    G-code, и voxel-симуляцию съёма материала для визуализации на
    фронтенде. Требует STEP (для геометрии) и чертёж (для марки
    материала из штампа) — деталь без топологии/материала получает
    честный unsupported_warning, не выдуманную траекторию.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        step_path = Path(tmp_dir) / (step_model.filename or "model.step")
        step_path.write_bytes(await step_model.read())
        drawing_path = Path(tmp_dir) / (drawing.filename or "drawing.pdf")
        drawing_path.write_bytes(await drawing.read())

        drawing_model = await run_heavy(_drawing_parser.parse, drawing_path)
        part_name = drawing_model.title_block.part_name if drawing_model else None
        material_grade = drawing_model.title_block.material if drawing_model else None

        settings = get_settings()
        pipeline_result = await run_heavy(
            run_toolpath_pipeline,
            step_path=step_path,
            pythonocc_python_path=settings.pythonocc_python_path,
            metal_db_path=_get_metal_db_path(),
            part_name=part_name,
            material_grade=material_grade,
        )

    return _toolpath_pipeline_result_to_dict(pipeline_result)


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
            blank_designation=drawing_model.title_block.blank_designation if drawing_model else None,
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
            bounding_box=step.bounding_box,
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

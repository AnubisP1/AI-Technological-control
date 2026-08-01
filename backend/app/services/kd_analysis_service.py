"""Сервис Модуля 1.1: анализ загруженного комплекта КД.

Оркестрирует парсеры чертежа, детектор видов и парсер STEP-модели через
worker_pool, чтобы разбор не блокировал event loop FastAPI (см.
docs/ARCHITECTURE.md, "Тяжёлые задачи"). Все зависимости внедряются
через порты domain — сервис не знает, какая конкретная реализация
используется (напр. PdfDrawingParser/OcrDrawingParser через
AutoDrawingParser, RegexStepParser).
"""

from __future__ import annotations

from pathlib import Path

from app.domain.cad.drawing_parser_port import IDrawingParser
from app.domain.cad.kd_analysis import KdAnalysisResult
from app.domain.cad.step_parser_port import IStepParser
from app.domain.cad.view_detector_port import IViewDetector
from app.infrastructure.worker_pool import run_heavy


class KdAnalysisService:
    def __init__(
        self,
        drawing_parser: IDrawingParser,
        view_detector: IViewDetector,
        step_parser: IStepParser,
    ) -> None:
        self._drawing_parser = drawing_parser
        self._view_detector = view_detector
        self._step_parser = step_parser

    async def analyze(
        self, *, drawing_path: Path | None, step_path: Path | None
    ) -> KdAnalysisResult:
        drawing = None
        view_detection = None
        if drawing_path is not None:
            drawing = await run_heavy(self._drawing_parser.parse, drawing_path)
            view_detection = await run_heavy(self._view_detector.detect, drawing_path)

        step_model = None
        if step_path is not None:
            step_model = await run_heavy(self._step_parser.parse, step_path)

        return KdAnalysisResult(
            drawing=drawing, view_detection=view_detection, step_model=step_model
        )

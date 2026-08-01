"""Сервис Модуля 1.1: анализ загруженного комплекта КД.

Оркестрирует парсеры чертежа и STEP-модели через worker_pool, чтобы
разбор не блокировал event loop FastAPI (см. docs/ARCHITECTURE.md,
"Тяжёлые задачи"). Парсеры внедряются через порты domain — сервис не
знает, что за конкретной реализацией (PdfDrawingParser/RegexStepParser).
"""

from __future__ import annotations

from pathlib import Path

from app.domain.cad.drawing_parser_port import IDrawingParser
from app.domain.cad.kd_analysis import KdAnalysisResult
from app.domain.cad.step_parser_port import IStepParser
from app.infrastructure.worker_pool import run_heavy


class KdAnalysisService:
    def __init__(self, drawing_parser: IDrawingParser, step_parser: IStepParser) -> None:
        self._drawing_parser = drawing_parser
        self._step_parser = step_parser

    async def analyze(
        self, *, drawing_path: Path | None, step_path: Path | None
    ) -> KdAnalysisResult:
        drawing = None
        if drawing_path is not None:
            drawing = await run_heavy(self._drawing_parser.parse, drawing_path)

        step_model = None
        if step_path is not None:
            step_model = await run_heavy(self._step_parser.parse, step_path)

        return KdAnalysisResult(drawing=drawing, step_model=step_model)

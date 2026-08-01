"""Порт (интерфейс) STEP-парсера — domain не знает, использует ли
конкретная реализация регулярные выражения или pythonocc-core.

См. dev/QUESTIONS.md №1 и docs/ARCHITECTURE.md: на Python 3.11 baseline —
RegexStepParser (infrastructure/cad/regex_step_parser.py); точный B-rep
для UV-Net (pythonocc-core) подключается позже как вторая реализация
этого же порта, без изменений в вызывающем коде.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from app.domain.cad.step_model import StepModel


class IStepParser(Protocol):
    def parse(self, file_path: Path) -> StepModel: ...

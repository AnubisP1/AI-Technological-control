"""Универсальные шаблоны управляющих программ для симуляции Модуля 2.

По ТЗ: "для работы системы тут можно заранее написать универсальную
программу для металлических деталей и универсальную программу для
пластиковых деталей и просто в интерфейсе отображать процесс
построчного написания этой управляющей программы". Это заведомо не
результат реального постпроцессора/слайсера для конкретной детали —
условный текст, демонстрирующий сам процесс построчной генерации в UI.

Программа выбирается по типу станка/принтера (грубая категория), а не
генерируется из геометрии — реальный расчёт траекторий вне объёма
проекта (см. dev/QUESTIONS.md, режимы резания/параметры печати
отложены на реализацию после завершения основного плана).
"""

from __future__ import annotations

_TURNING_PROGRAM = (
    "%",
    "O0001 (УНИВЕРСАЛЬНАЯ ПРОГРАММА ТОЧЕНИЯ)",
    "G21 G40 G80 G90",
    "T0101",
    "G96 S180 M03",
    "G00 X50. Z2.",
    "G01 X-1. F0.2",
    "G00 X50. Z2.",
    "G00 X48. Z2.",
    "G01 Z-40. F0.15",
    "G00 X50.",
    "G00 Z2.",
    "T0202",
    "G96 S220 M03",
    "G01 X30. Z0. F0.1",
    "G01 Z-38.",
    "G00 X50. Z2.",
    "M09",
    "M05",
    "M30",
    "%",
)

_MILLING_PROGRAM = (
    "%",
    "O0002 (УНИВЕРСАЛЬНАЯ ПРОГРАММА ФРЕЗЕРОВАНИЯ)",
    "G21 G40 G80 G90",
    "T01 M06",
    "G54 G00 X0 Y0",
    "S3000 M03",
    "G00 Z5.",
    "G01 Z-2. F100",
    "G01 X60. F300",
    "G01 Y40.",
    "G01 X0.",
    "G01 Y0.",
    "G00 Z5.",
    "M09",
    "M05",
    "M30",
    "%",
)

_DRILLING_PROGRAM = (
    "%",
    "O0003 (УНИВЕРСАЛЬНАЯ ПРОГРАММА СВЕРЛЕНИЯ)",
    "G21 G40 G80 G90",
    "T03 M06",
    "G54 G00 X10. Y10.",
    "S1500 M03",
    "G83 Z-15. R2. Q3. F80",
    "X30. Y10.",
    "X30. Y30.",
    "X10. Y30.",
    "G80",
    "G00 Z50.",
    "M05",
    "M30",
    "%",
)

_GRINDING_PROGRAM = (
    "%",
    "O0004 (УНИВЕРСАЛЬНАЯ ПРОГРАММА ШЛИФОВАНИЯ)",
    "G21 G90",
    "G00 X0 Z0",
    "S1800 M03",
    "G01 X-0.05 F0.02",
    "G04 P2000",
    "G01 X0.05 F0.02",
    "G00 Z50.",
    "M05",
    "M30",
    "%",
)

_FALLBACK_METAL_PROGRAM = _MILLING_PROGRAM

# Ключ — начало operation_type_code из БД НСИ (TURN_ROUGH/TURN_FIN, MILL,
# DRILL, GRIND, CONTROL — см. _OPERATION_ORDER в process_planning_service.py).
# Матчинг по коду, а не по русскому названию станка — коды стабильны и не
# зависят от формулировок в справочнике.
_METAL_PROGRAMS_BY_OPERATION_PREFIX: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("TURN", _TURNING_PROGRAM),
    ("MILL", _MILLING_PROGRAM),
    ("DRILL", _DRILLING_PROGRAM),
    ("GRIND", _GRINDING_PROGRAM),
)


def metal_program_for_operation_type_code(operation_type_code: str) -> tuple[str, ...]:
    """Возвращает () для нестаночных операций (напр. CONTROL) — контроль
    не выполняется на станке с ЧПУ, управляющей программы для него нет."""
    upper_code = operation_type_code.upper()
    if upper_code.startswith("CONTROL"):
        return ()
    for prefix, program in _METAL_PROGRAMS_BY_OPERATION_PREFIX:
        if upper_code.startswith(prefix):
            return program
    return _FALLBACK_METAL_PROGRAM


_FDM_PROGRAM = (
    "; УНИВЕРСАЛЬНАЯ ПРОГРАММА FDM-ПЕЧАТИ",
    "G21 ; единицы — миллиметры",
    "G90 ; абсолютное позиционирование",
    "M104 S210 ; нагрев сопла",
    "M140 S60 ; нагрев стола",
    "G28 ; парковка по всем осям",
    "G1 Z0.2 F300",
    "G1 X10 Y10 F1500",
    "G1 X100 Y10 E5.0 F900",
    "G1 X100 Y100 E10.0",
    "G1 X10 Y100 E15.0",
    "G1 X10 Y10 E20.0",
    "G1 Z0.4",
    "M104 S0",
    "M140 S0",
    "M84",
)

_SLA_PROGRAM = (
    "; УНИВЕРСАЛЬНАЯ ПРОГРАММА SLA/MSLA-ПЕЧАТИ",
    "; послойная засветка фотополимера",
    "LAYER 1 Z=0.05 EXPOSURE=8.0s",
    "LAYER 2 Z=0.10 EXPOSURE=8.0s",
    "LAYER 3 Z=0.15 EXPOSURE=6.0s",
    "LIFT Z=5.0 SPEED=60",
    "RETRACT SPEED=150",
    "...",
    "LAYER N Z=FINAL EXPOSURE=6.0s",
    "END",
)

_SLS_PROGRAM = (
    "; УНИВЕРСАЛЬНАЯ ПРОГРАММА SLS-ПЕЧАТИ",
    "PREHEAT_BED T=170C",
    "LAYER 1 THICKNESS=0.10 LASER_POWER=20W",
    "RECOAT",
    "LAYER 2 THICKNESS=0.10 LASER_POWER=20W",
    "RECOAT",
    "...",
    "LAYER N THICKNESS=0.10 LASER_POWER=20W",
    "COOLDOWN",
    "END",
)

_FALLBACK_PRINT_PROGRAM = _FDM_PROGRAM

_PRINT_PROGRAMS_BY_KEYWORD: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("FDM", _FDM_PROGRAM),
    ("SLA", _SLA_PROGRAM),
    ("SLS", _SLS_PROGRAM),
)


def print_program_for_printer_type(printer_type_name: str) -> tuple[str, ...]:
    upper_name = printer_type_name.upper()
    for keyword, program in _PRINT_PROGRAMS_BY_KEYWORD:
        if keyword in upper_name:
            return program
    return _FALLBACK_PRINT_PROGRAM

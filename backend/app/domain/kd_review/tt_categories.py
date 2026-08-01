"""Классификатор категорий технических требований (Модуль 1.2).

Категории и характерные паттерны формулировок взяты из структуры
`БД НСИ/Технические требования к чертежам.pdf` (см. dev/QUESTIONS.md №4,
dev/docs/ARCHITECTURE.md "Контекстная фильтрация технических требований") —
не изобретены заново. Правило-ориентированный классификатор (regex), а не
ML/LLM — соответствует Фазе 3 плана: LLM подключается только если
правил окажется недостаточно для семантического сопоставления
вариативных формулировок (см. docs/ARCHITECTURE.md, "Генерация текста").
"""

from __future__ import annotations

import re

# Порядок важен: первое совпадение побеждает — более специфичные
# категории (напр. "химико-термическая обработка") должны идти раньше
# более общих совпадений по ключевым словам ("обработка").
_CATEGORY_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("material", re.compile(r"материал\s*:", re.IGNORECASE)),
    (
        "chemical_thermal_treatment",
        re.compile(r"цементаци|азотирован|борирован|нитроцементаци", re.IGNORECASE),
    ),
    (
        "heat_treatment",
        re.compile(r"\bHRC\b|\bHB\b|\bHV\b|закал|отпуск|термическ", re.IGNORECASE),
    ),
    (
        "coating",
        re.compile(r"покрыти|никелирован|цинкован|оксидирован|хромирован", re.IGNORECASE),
    ),
    (
        "unspecified_tolerances",
        re.compile(
            r"неуказанн\w*\s+(предельн|допуск|радиус)|"
            r"H1[0-9]\s*,\s*h1[0-9]|±\s*IT\d+",
            re.IGNORECASE,
        ),
    ),
    (
        "form_position_tolerance",
        re.compile(r"допуск\w*\s+(форм|расположени)|общ\w*\s+допуск", re.IGNORECASE),
    ),
    ("roughness", re.compile(r"шероховатост|\bRa\b|\bRz\b", re.IGNORECASE)),
    (
        "process_sequence",
        re.compile(r"обрабатывать после|выполнять до|последовательност", re.IGNORECASE),
    ),
    (
        "inspection_testing",
        re.compile(
            r"контрол\w*\s+(герметичност|качеств)|балансировк|неразрушающ|"
            r"испытани",
            re.IGNORECASE,
        ),
    ),
    (
        "assembly",
        re.compile(r"момент\w*\s+затяжк|фиксатор|зазор", re.IGNORECASE),
    ),
    (
        "operating_conditions",
        re.compile(r"рабоч\w*\s+температур|ресурс|гарантийн", re.IGNORECASE),
    ),
    ("reference_dimension", re.compile(r"размер\w*\s+для\s+справок|справочн", re.IGNORECASE)),
    (
        "rounding_edges",
        re.compile(r"радиус\w*\s+скруглени|притупить|кромк\w*\s+притупить", re.IGNORECASE),
    ),
]


def classify_requirement(text: str) -> str | None:
    """Возвращает код категории или None, если ни один паттерн не совпал —
    не значит, что пункт некорректен, значит лишь, что он не распознан
    правилами (см. KdReviewFinding по нераспознанным пунктам)."""
    for category, pattern in _CATEGORY_PATTERNS:
        if pattern.search(text):
            return category
    return None

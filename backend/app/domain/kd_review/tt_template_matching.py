"""Сверка пунктов технических требований чертежа с типовыми
формулировками ОСТ 1 02504-84 (Модуль 1.2).

Зачем: ГОСТ Р 2.316 задаёт правила ОФОРМЛЕНИЯ технических требований
(нумерация, расположение, последовательность), но не сами формулировки.
Формулировки для авиационных чертежей устанавливает отраслевой стандарт
ОСТ 1 02504-84 — его таблицы и лежат в справочнике НСИ. Совпадение с
типовой формулировкой означает, что пункт написан «по стандарту», а
расхождение — повод технологу перечитать пункт, но НЕ нарушение:
стандарт не запрещает формулировать иначе, если требование понятно.

Сопоставление нечёткое: в типовой формулировке стоят прочерки-поля
(«HRC ___», «Неуказанные предельные отклонения толщин - ____ мм»),
которые конструктор заполняет конкретными значениями. Сравнивать такие
строки посимвольно бессмысленно, поэтому сравниваются наборы значимых
слов.
"""

from __future__ import annotations

import re

from app.domain.cad.drawing_model import TechnicalRequirement
from app.domain.kd_review.tt_template_port import TypicalRequirementTemplate

# Доля слов типовой формулировки, которую должен покрыть пункт чертежа,
# чтобы считаться написанным по этой формулировке. 0.6 подобрана так,
# чтобы «Неуказанные предельные отклонения размеров, допуски формы и
# расположения поверхностей по ОСТ 1 00022-80» совпало с типовой
# «Неуказанные предельные отклонения размеров - по ОСТ 1 00022-80»
# (конструктор дописал уточнение), но не совпало с посторонним пунктом.
_MATCH_RATIO = 0.6

# Прочерки-поля источника: «___», «_____», «- ___ мм».
_RE_PLACEHOLDER = re.compile(r"_{2,}")
# Служебные слова, не несущие смысла при сопоставлении.
_STOP_WORDS = frozenset({"и", "или", "по", "с", "в", "на", "не", "для", "то", "же", "от", "до"})


def _significant_words(text: str) -> set[str]:
    """Значимые слова строки: без прочерков, пунктуации и предлогов.

    Числа сохраняются — в обозначениях стандартов («ОСТ 1 00022-80»)
    именно они несут различающую информацию.
    """
    cleaned = _RE_PLACEHOLDER.sub(" ", text.lower())
    words = re.findall(r"[a-zа-яё0-9]+(?:[.\-][a-zа-яё0-9]+)*", cleaned)
    return {w for w in words if w not in _STOP_WORDS and len(w) > 1}


def match_typical_requirement(
    requirement: TechnicalRequirement,
    templates: tuple[TypicalRequirementTemplate, ...],
) -> TypicalRequirementTemplate | None:
    """Типовая формулировка, которой соответствует пункт ТТ чертежа.

    Возвращает None, если ни одна не покрыта достаточно — это НЕ ошибка
    чертежа, а лишь отсутствие совпадения со справочником.
    """
    requirement_words = _significant_words(requirement.text)
    if not requirement_words:
        return None

    best: tuple[float, TypicalRequirementTemplate] | None = None
    for template in templates:
        template_words = _significant_words(template.formulation_template)
        if not template_words:
            continue
        covered = len(template_words & requirement_words) / len(template_words)
        if covered >= _MATCH_RATIO and (best is None or covered > best[0]):
            best = (covered, template)

    return best[1] if best else None

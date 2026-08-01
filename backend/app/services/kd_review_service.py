"""Сервис Модуля 1.2: генерация отчёта об оценке КД по результатам сверки
с БД НСИ. По ТЗ оценивает: (1) корректность технических требований,
(2) доступность материала, указанного в заготовке, (3) формирует
обратную связь на этап проектирования при рисках/невозможности
изготовления.
"""

from __future__ import annotations

from app.domain.cad.drawing_model import DrawingModel
from app.domain.kd_review.material_matching import match_blank, match_material
from app.domain.kd_review.nsi_lookup_port import INsiLookup
from app.domain.kd_review.review_model import (
    KdReviewFinding,
    KdReviewReport,
    MatchStatus,
    TechnicalRequirementCheck,
)
from app.domain.kd_review.tt_categories import classify_requirement


class KdReviewService:
    def __init__(self, nsi_lookup: INsiLookup) -> None:
        self._nsi_lookup = nsi_lookup

    def review(self, drawing: DrawingModel | None) -> KdReviewReport:
        if drawing is None:
            return KdReviewReport(
                material_check=None,
                blank_check=None,
                findings=(
                    KdReviewFinding(
                        severity="blocking",
                        message=(
                            "Чертёж не предоставлен или не распознан — сверка "
                            "материала/заготовки и оценка технических требований "
                            "невозможны без основной надписи чертежа."
                        ),
                    ),
                ),
            )

        materials = self._nsi_lookup.find_materials()
        blanks = self._nsi_lookup.find_workpiece_blanks()

        material_check = match_material(drawing.title_block.material, materials)
        blank_check = match_blank(drawing.title_block.blank_designation, blanks)

        tt_checks = tuple(
            TechnicalRequirementCheck(
                number=req.number,
                text=req.text,
                is_recognized=classify_requirement(req.text) is not None,
                category=classify_requirement(req.text),
            )
            for req in drawing.technical_requirements
        )

        findings = self._build_findings(material_check, blank_check, tt_checks)

        return KdReviewReport(
            material_check=material_check,
            blank_check=blank_check,
            technical_requirement_checks=tt_checks,
            findings=findings,
        )

    def _build_findings(
        self, material_check, blank_check, tt_checks: tuple[TechnicalRequirementCheck, ...]
    ) -> tuple[KdReviewFinding, ...]:
        findings: list[KdReviewFinding] = []

        if material_check.status == MatchStatus.NOT_FOUND:
            findings.append(
                KdReviewFinding(
                    severity="blocking",
                    message=(
                        f"Материал '{material_check.material_from_drawing}' не найден "
                        "в справочнике НСИ — доступность на предприятии не подтверждена. "
                        "Обратная связь конструктору: проверить обозначение материала "
                        "или согласовать замену на материал из действующей НСИ."
                    ),
                )
            )
        elif material_check.status == MatchStatus.PARTIAL_MATCH:
            findings.append(
                KdReviewFinding(
                    severity="warning",
                    message=(
                        f"Материал '{material_check.material_from_drawing}' частично "
                        f"совпадает со справочником НСИ ({material_check.note}) — "
                        "требуется проверка технологом перед запуском в производство."
                    ),
                )
            )

        if blank_check.status == MatchStatus.NOT_FOUND:
            findings.append(
                KdReviewFinding(
                    severity="warning",
                    message=(
                        f"Заготовка '{blank_check.blank_from_drawing}' не найдена "
                        "в справочнике НСИ — типоразмер для закупки не подтверждён."
                    ),
                )
            )
        elif blank_check.status == MatchStatus.PARTIAL_MATCH:
            findings.append(
                KdReviewFinding(
                    severity="info",
                    message=(
                        f"Заготовка '{blank_check.blank_from_drawing}': {blank_check.note}"
                    ),
                )
            )

        unrecognized = [tt for tt in tt_checks if not tt.is_recognized]
        if unrecognized:
            numbers = ", ".join(str(tt.number) for tt in unrecognized)
            findings.append(
                KdReviewFinding(
                    severity="info",
                    message=(
                        f"Пункты технических требований № {numbers} не отнесены "
                        "ни к одной известной категории (материал, термообработка, "
                        "покрытие, допуски, шероховатость и т.д.) — требуется "
                        "проверка технологом на предмет нестандартных формулировок."
                    ),
                )
            )

        return tuple(findings)

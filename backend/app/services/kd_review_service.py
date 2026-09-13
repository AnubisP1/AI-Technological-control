"""Сервис Модуля 1.2: генерация отчёта об оценке КД по результатам сверки
с БД НСИ. По ТЗ оценивает: (1) корректность технических требований,
(2) доступность материала, указанного в заготовке, (3) формирует
обратную связь на этап проектирования при рисках/невозможности
изготовления.
"""

from __future__ import annotations

import logging

from app.domain.cad.drawing_model import DrawingModel
from app.domain.kd_review.gost_checking import (
    check_general_roughness_format,
    check_material_designation,
    check_plate_blank_sortament,
    check_plate_material_attributes,
    check_scale,
    check_technical_requirements_numbering,
    check_technical_requirements_order,
    check_title_block,
)
from app.domain.kd_review.gost_lookup_port import IGostLookup
from app.domain.kd_review.material_matching import match_blank, match_material
from app.domain.kd_review.nsi_lookup_port import INsiLookup
from app.domain.kd_review.review_model import (
    GostCheckStatus,
    GostRequirementCheck,
    KdReviewFinding,
    KdReviewReport,
    MaterialCheck,
    MatchStatus,
    ReviewSummary,
    TechnicalRequirementCheck,
)
from app.domain.material_text import extract_plate_material_attributes
from app.domain.kd_review.text_generator_port import ITextGenerator
from app.domain.kd_review.tt_template_matching import match_typical_requirement
from app.domain.kd_review.tt_template_port import ITypicalRequirementLookup
from app.domain.kd_review.tt_categories import classify_requirement
from app.infrastructure.llm.template_text_generator import TemplateTextGenerator

logger = logging.getLogger(__name__)


class KdReviewService:
    def __init__(
        self,
        nsi_lookup: INsiLookup,
        text_generator: ITextGenerator | None = None,
        gost_lookup: IGostLookup | None = None,
        typical_requirement_lookup: ITypicalRequirementLookup | None = None,
    ) -> None:
        self._nsi_lookup = nsi_lookup
        self._template_text_generator = TemplateTextGenerator()
        # text_generator опционален — если не передан (обычный запуск без
        # настроенного пути к локальной модели Qwen), используется только
        # шаблонный путь.
        self._text_generator = text_generator
        # gost_lookup опционален по той же причине совместимости: без него
        # раздел проверок оформления по ГОСТ остаётся ПУСТЫМ, а не
        # "пройденным" — отсутствие проверки не выдаётся за её успех.
        self._gost_lookup = gost_lookup
        # Справочник типовых формулировок ТТ (ОСТ 1 02504-84). Без него
        # раздел сверки формулировок просто отсутствует, а не считается
        # пройденным — отсутствие проверки не выдаётся за её успех.
        self._typical_requirement_lookup = typical_requirement_lookup

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

        material_check = match_material(
            drawing.title_block.material, materials, blanks
        )
        material_check = self._confirm_plate_material_attributes(
            drawing, material_check
        )
        blank_check = match_blank(drawing.title_block.blank_designation, blanks)

        tt_checks = self._check_technical_requirements(drawing)

        gost_checks = self._run_gost_checks(drawing)
        # Порядок изложения ТТ проверяется по уже определённым категориям
        # пунктов, поэтому идёт после _check_technical_requirements.
        order_check = check_technical_requirements_order(tt_checks)
        if order_check is not None:
            gost_checks = gost_checks + (order_check,)

        findings = self._build_findings(material_check, blank_check, tt_checks, drawing)
        findings = findings + self._gost_findings(gost_checks)
        # Предупреждение о качестве скана идёт ПЕРВЫМ: оно объясняет
        # причину остальных «не распознано» и без него отчёт вводит в
        # заблуждение.
        scan_finding = self._low_resolution_finding(drawing)
        if scan_finding is not None:
            findings = (scan_finding,) + findings
        summary = self._summarize(findings, material_check, materials)

        return KdReviewReport(
            material_check=material_check,
            blank_check=blank_check,
            technical_requirement_checks=tt_checks,
            gost_checks=gost_checks,
            findings=findings,
            summary=summary,
        )

    def _confirm_plate_material_attributes(
        self,
        drawing: DrawingModel,
        material_check: MaterialCheck,
    ) -> MaterialCheck:
        """Повышает partial match до matched только после ГОСТ-проверки.

        Марка сплава подтверждается материальной НСИ, а буквы после неё —
        справочными перечнями плакировки и состояния в ГОСТ 17232-2023.
        """
        if (
            material_check.status is not MatchStatus.PARTIAL_MATCH
            or material_check.matched_grade is None
            or self._gost_lookup is None
        ):
            return material_check
        attributes = extract_plate_material_attributes(
            drawing.title_block.blank_designation or ""
        )
        if attributes is None:
            return material_check
        expected_count = sum(
            value is not None
            for value in (attributes.plating, attributes.material_state)
        )
        if expected_count == 0:
            return material_check
        try:
            checks = check_plate_material_attributes(
                drawing, self._gost_lookup.find_enum_requirements()
            )
        except Exception:
            return material_check
        if len(checks) != expected_count or any(
            check.status is not GostCheckStatus.PASSED for check in checks
        ):
            return material_check

        condition = " ".join(
            value
            for value in (attributes.plating, attributes.material_state)
            if value is not None
        )
        return MaterialCheck(
            material_from_drawing=material_check.material_from_drawing,
            status=MatchStatus.MATCHED,
            matched_grade=material_check.matched_grade,
            matched_gost=material_check.matched_gost,
            note=(
                f"Материал указан верно: марка {attributes.grade} найдена в НСИ; "
                f"состояние {condition} стандартом ГОСТ 17232-2023 допускается "
                "(А — нормальная плакировка; Т — закалённое и "
                "естественно состаренное)."
            ),
        )

    def _check_technical_requirements(
        self, drawing: DrawingModel
    ) -> tuple[TechnicalRequirementCheck, ...]:
        """Категория пункта ТТ плюс сверка формулировки с типовой.

        Категория (tt_categories) отвечает на вопрос «о чём этот пункт»,
        сверка с ОСТ 1 02504-84 — «написан ли он стандартной
        формулировкой». Это разные вещи: пункт может быть понятной
        категории, но сформулирован произвольно.
        """
        templates: tuple = ()
        if self._typical_requirement_lookup is not None:
            try:
                templates = self._typical_requirement_lookup.find_typical_requirements()
            except Exception:
                # Недоступный справочник не должен ронять отчёт: сверка с
                # НСИ и проверки ГОСТ остаются валидными.
                logger.warning(
                    "Справочник типовых формулировок ТТ недоступен", exc_info=True
                )

        checks: list[TechnicalRequirementCheck] = []
        for requirement in drawing.technical_requirements:
            category = classify_requirement(requirement.text)
            template = (
                match_typical_requirement(requirement, templates) if templates else None
            )
            checks.append(
                TechnicalRequirementCheck(
                    number=requirement.number,
                    text=requirement.text,
                    is_recognized=category is not None,
                    category=category,
                    typical_template_code=template.code if template else None,
                    typical_formulation=(
                        template.formulation_template if template else None
                    ),
                    typical_reference_standard=(
                        template.reference_standard if template else None
                    ),
                )
            )
        return tuple(checks)

    @staticmethod
    def _low_resolution_finding(drawing: DrawingModel) -> KdReviewFinding | None:
        """Честное объяснение, почему поля не распознаны, когда причина —
        качество файла, а не содержание чертежа."""
        if not drawing.is_low_resolution_scan:
            return None
        return KdReviewFinding(
            severity="warning",
            message=(
                f"Чертёж — скан с эффективным разрешением ≈{drawing.raster_dpi:.0f} точек "
                "на дюйм. При таком разрешении строки основной надписи имеют высоту "
                "порядка одного-двух пикселей и не читаются никаким средством "
                "распознавания. Поля «Материал», «Заготовка», «Масштаб», «Масса» не "
                "распознаны по причине качества исходного файла, а НЕ потому, что они "
                "отсутствуют на чертеже. Требуется повторное сканирование с разрешением "
                "не ниже 300 точек на дюйм либо исходный файл с текстовым слоем."
            ),
        )

    def _run_gost_checks(self, drawing: DrawingModel) -> tuple[GostRequirementCheck, ...]:
        """Проверка оформления чертежа по ГОСТ ЕСКД.

        Часть проверок (нумерация ТТ, форма записи материала) не требует
        обращения к базе — их правила закодированы в самом пункте
        стандарта и не имеют вариативных данных. Часть (масштаб, графы
        штампа) читает требования из базы ГОСТ; без неё эти проверки
        просто не выполняются.
        """
        checks: list[GostRequirementCheck] = []

        # Не зависят от базы ГОСТ — работают всегда, когда есть чертёж.
        tt_numbering = check_technical_requirements_numbering(drawing)
        if tt_numbering is not None:
            checks.append(tt_numbering)
        checks.append(check_material_designation(drawing))

        if self._gost_lookup is None:
            return tuple(checks)

        try:
            enum_requirements = self._gost_lookup.find_enum_requirements()
            scale_check = check_scale(drawing, enum_requirements)
            if scale_check is not None:
                checks.append(scale_check)
            checks.extend(
                check_plate_material_attributes(drawing, enum_requirements)
            )
            checks.extend(check_title_block(drawing, self._gost_lookup.find_title_block_fields()))
            find_procedural = getattr(
                self._gost_lookup, "find_procedural_requirements", lambda: ()
            )
            roughness_check = check_general_roughness_format(
                drawing, find_procedural()
            )
            if roughness_check is not None:
                checks.append(roughness_check)
            # Сортамент заготовки (ГОСТ 17232-2023) — единственная проверка
            # не по ЕСКД: сверяет не оформление, а реальную выпускаемость
            # указанной заготовки.
            sortament_check = check_plate_blank_sortament(
                drawing, self._gost_lookup.find_numeric_requirements()
            )
            if sortament_check is not None:
                checks.append(sortament_check)
        except Exception:
            # Недоступная база ГОСТ не должна ронять весь отчёт: сверка с
            # НСИ и оценка ТТ остаются валидными. Проверки оформления при
            # этом отсутствуют в отчёте — и это видно, потому что раздел
            # окажется неполным, а не помечен пройденным.
            logger.warning(
                "Проверки оформления по ГОСТ недоступны — база требований не прочитана",
                exc_info=True,
            )

        return tuple(checks)

    @staticmethod
    def _gost_findings(
        gost_checks: tuple[GostRequirementCheck, ...],
    ) -> tuple[KdReviewFinding, ...]:
        """Переводит нарушения ГОСТ в находки обратной связи конструктору.

        Severity 'warning', а не 'blocking': нарушение правил ОФОРМЛЕНИЯ
        (масштаб вне ряда, незаполненная графа) не делает изготовление
        детали невозможным — в отличие от отсутствия материала в НСИ.
        Блокировать согласование из-за оформления было бы неверно.
        NEEDS_REVIEW даёт 'info' — это не нарушение, а место для решения
        технолога.
        """
        findings: list[KdReviewFinding] = []
        for check in gost_checks:
            if check.status is GostCheckStatus.VIOLATED:
                actual = f" Фактически: «{check.actual_value}»." if check.actual_value else ""
                findings.append(
                    KdReviewFinding(
                        severity="warning",
                        message=(
                            f"{check.standard_designation}, п. {check.clause_number}: "
                            f"{check.parameter_name} — не соответствует.{actual} "
                            f"{check.note}"
                        ).strip(),
                    )
                )
            elif check.status is GostCheckStatus.NEEDS_REVIEW:
                findings.append(
                    KdReviewFinding(
                        severity="info",
                        message=(
                            f"{check.standard_designation}, п. {check.clause_number}: "
                            f"{check.parameter_name} — требует проверки технологом. "
                            f"{check.note}"
                        ).strip(),
                    )
                )
        return tuple(findings)

    def _summarize(
        self,
        findings: tuple[KdReviewFinding, ...],
        material_check,
        known_materials: tuple,
    ) -> ReviewSummary:
        # candidate_materials — ВСЯ база материалов с их технологическими
        # свойствами (плотность/прочность/твёрдость/индекс обрабатываемости),
        # не только выбранный, — чтобы LLM могла реально сравнить и
        # предложить аналог (Фаза 18), а не просто переформулировать один
        # уже найденный факт. Findings остаются анти-галлюцинационным
        # якорем: генератору запрещено выйти за пределы findings+фактов
        # НСИ ниже (см. системный промпт QwenTextGenerator).
        facts = {
            "findings": [{"severity": f.severity, "message": f.message} for f in findings],
            "matched_material": (
                {
                    "grade": material_check.matched_grade,
                    "gost_standard": material_check.matched_gost,
                }
                if material_check is not None and material_check.matched_grade
                else None
            ),
            "candidate_materials": [
                {
                    "grade": m.grade,
                    "gost_standard": m.gost_standard,
                    "density_kg_m3": m.density_kg_m3,
                    "tensile_strength_mpa": m.tensile_strength_mpa,
                    "hardness_hb": m.hardness_hb,
                    "hardness_hrc": m.hardness_hrc,
                    "red_hardness_c": m.red_hardness_c,
                    "machinability_index": m.machinability_index,
                    "chemical_composition": m.chemical_composition,
                    "heat_treatment": m.heat_treatment,
                    "application": m.application,
                }
                for m in known_materials
            ],
        }

        if self._text_generator is not None:
            try:
                generated = self._text_generator.summarize_review(facts=facts)
                return ReviewSummary(text=generated.text, generated_by=generated.generated_by)
            except Exception:
                # Модель недоступна/не загружена/ошибка инференса — любая
                # причина не должна ронять отчёт целиком. Откатываемся на
                # шаблонный текст, который всегда доступен офлайн (см.
                # QUESTIONS.md №12/№14).
                logger.warning(
                    "Локальный LLM недоступен, используется шаблонный fallback",
                    exc_info=True,
                )

        generated = self._template_text_generator.summarize_review(facts=facts)
        return ReviewSummary(text=generated.text, generated_by=generated.generated_by)

    def _build_findings(
        self,
        material_check,
        blank_check,
        tt_checks: tuple[TechnicalRequirementCheck, ...],
        drawing: DrawingModel | None = None,
    ) -> tuple[KdReviewFinding, ...]:
        findings: list[KdReviewFinding] = []
        # На нечитаемом скане отсутствие материала — свойство ФАЙЛА, а не
        # чертежа. Блокировать согласование в этом случае неверно:
        # has_blocking_findings управляет решением главного технолога
        # (см. approval_service.py), а материал на чертеже указан и корректен.
        unreadable_scan = drawing is not None and drawing.is_low_resolution_scan

        if material_check.status == MatchStatus.NOT_FOUND:
            if unreadable_scan and not material_check.material_from_drawing:
                findings.append(
                    KdReviewFinding(
                        severity="info",
                        message=(
                            "Материал не сверен с НСИ: он не прочитан из-за качества "
                            "скана (см. предупреждение о разрешении выше). Загрузите "
                            "чертёж в исходном качестве, чтобы выполнить сверку."
                        ),
                    )
                )
            else:
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
            if unreadable_scan and not blank_check.blank_from_drawing:
                findings.append(
                    KdReviewFinding(
                        severity="info",
                        message=(
                            "Заготовка не сверена с НСИ: она не прочитана из-за качества "
                            "скана (см. предупреждение о разрешении выше)."
                        ),
                    )
                )
            else:
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

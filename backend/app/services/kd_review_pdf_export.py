"""Экспорт отчёта КД (Модуль 1.2) в PDF — Фаза 8, визуальное улучшение
по запросу пользователя (см. dev/QUESTIONS.md №12).

Через PyMuPDF (уже зависимость проекта — используется в парсинге
чертежей, здесь применяется в обратную сторону, для генерации, а не
чтения PDF). Простой текстовый layout — дерево проверок через отступы,
статусы через цвет текста, без внешних PDF-библиотек/шаблонизаторов.
"""

from __future__ import annotations

import io

import fitz

from app.domain.kd_review.review_model import (
    GostCheckStatus,
    KdReviewReport,
    MatchStatus,
)

_PAGE_WIDTH, _PAGE_HEIGHT = fitz.paper_size("a4")
_MARGIN = 40
_LINE_HEIGHT = 16

_COLOR_TEXT = (0.1, 0.1, 0.15)
_COLOR_OK = (0.02, 0.45, 0.2)
_COLOR_WARN = (0.55, 0.4, 0.0)
_COLOR_ERROR = (0.65, 0.1, 0.1)
_COLOR_MUTED = (0.4, 0.45, 0.5)

_STATUS_COLOR = {
    MatchStatus.MATCHED: _COLOR_OK,
    MatchStatus.PARTIAL_MATCH: _COLOR_WARN,
    MatchStatus.NOT_FOUND: _COLOR_ERROR,
}
_STATUS_LABEL = {
    MatchStatus.MATCHED: "совпадение",
    MatchStatus.PARTIAL_MATCH: "частичное совпадение",
    MatchStatus.NOT_FOUND: "не найдено",
}
_SEVERITY_COLOR = {"blocking": _COLOR_ERROR, "warning": _COLOR_WARN, "info": _COLOR_MUTED}

# Проверки оформления по ГОСТ ЕСКД (Фаза 23). NOT_APPLICABLE в отчёт не
# печатается вовсе — «требование не применимо» не является результатом
# проверки и только удлинило бы документ.
_GOST_STATUS_LABEL = {
    GostCheckStatus.PASSED: "соответствует",
    GostCheckStatus.VIOLATED: "НАРУШЕНИЕ",
    GostCheckStatus.NEEDS_REVIEW: "требует проверки технологом",
    GostCheckStatus.NOT_APPLICABLE: "не применимо",
}
_GOST_STATUS_COLOR = {
    GostCheckStatus.PASSED: _COLOR_OK,
    GostCheckStatus.VIOLATED: _COLOR_ERROR,
    GostCheckStatus.NEEDS_REVIEW: _COLOR_WARN,
    GostCheckStatus.NOT_APPLICABLE: _COLOR_MUTED,
}


class _PdfCursor:
    """Простой построчный курсор с автопереносом на новую страницу —
    PyMuPDF не даёт готового потокового текстового layout.

    Использует fitz.TextWriter, а не Page.insert_text() напрямую: базовые
    Base14-шрифты ('helv'/'hebo'), переданные по имени в insert_text(),
    не поддерживают кириллицу (глифы вне latin1 просто не рисуются) —
    TextWriter с объектом fitz.Font('helv') кириллицу рендерит корректно
    (шрифт тот же, отличается только API встраивания текста).

    TextWriter.append() не принимает цвет построчно — цвет применяется
    целиком при write_text(page, color=...). Поэтому держим отдельный
    TextWriter на каждый использованный цвет и на каждой странице
    записываем их все по очереди при переходе на новую страницу/финализации."""

    def __init__(self, doc: fitz.Document) -> None:
        self._doc = doc
        self._regular_font = fitz.Font("helv")
        self._bold_font = fitz.Font("hebo")
        self._page = doc.new_page(width=_PAGE_WIDTH, height=_PAGE_HEIGHT)
        self._writers_by_color: dict[tuple, fitz.TextWriter] = {}
        self._y = _MARGIN

    def _writer_for(self, color: tuple) -> fitz.TextWriter:
        if color not in self._writers_by_color:
            self._writers_by_color[color] = fitz.TextWriter(self._page.rect)
        return self._writers_by_color[color]

    def _flush_page(self) -> None:
        for color, writer in self._writers_by_color.items():
            writer.write_text(self._page, color=color)
        self._writers_by_color = {}

    def line(self, text: str, *, indent: int = 0, size: float = 11, color=_COLOR_TEXT, bold=False) -> None:
        if self._y > _PAGE_HEIGHT - _MARGIN:
            self._flush_page()
            self._page = self._doc.new_page(width=_PAGE_WIDTH, height=_PAGE_HEIGHT)
            self._y = _MARGIN
        font = self._bold_font if bold else self._regular_font
        self._writer_for(color).append((_MARGIN + indent, self._y), text, font=font, fontsize=size)
        self._y += _LINE_HEIGHT * (size / 11)

    def wrapped_line(
        self, text: str, *, indent: int = 0, size: float = 11, color=_COLOR_TEXT, bold=False
    ) -> None:
        """Как line(), но переносит текст по словам, если он не влезает
        в ширину страницы — иначе длинные находки/резюме обрезались бы
        за правым краем листа."""
        font = self._bold_font if bold else self._regular_font
        max_width = _PAGE_WIDTH - _MARGIN - (_MARGIN + indent)

        words = text.split(" ")
        current = ""
        for word in words:
            candidate = f"{current} {word}".strip()
            if font.text_length(candidate, fontsize=size) > max_width and current:
                self.line(current, indent=indent, size=size, color=color, bold=bold)
                current = word
            else:
                current = candidate
        if current:
            self.line(current, indent=indent, size=size, color=color, bold=bold)

    def gap(self, size: float = 8) -> None:
        self._y += size

    def finish(self) -> None:
        self._flush_page()


def generate_kd_review_pdf(report: KdReviewReport, *, part_name: str | None) -> bytes:
    doc = fitz.open()
    cursor = _PdfCursor(doc)

    cursor.line("Отчёт об оценке конструкторской документации", size=16, bold=True)
    if part_name:
        cursor.line(f"Деталь: {part_name}", size=11, color=_COLOR_MUTED)
    cursor.gap(10)

    cursor.line("Дерево проверок", size=13, bold=True)
    cursor.gap(4)

    if report.material_check is not None:
        mc = report.material_check
        cursor.line("Материал", indent=0, bold=True)
        cursor.line(
            f"— {mc.material_from_drawing or '—'}: {_STATUS_LABEL[mc.status]}",
            indent=16,
            color=_STATUS_COLOR[mc.status],
        )
        if mc.note:
            cursor.wrapped_line(f"— {mc.note}", indent=32, size=10, color=_COLOR_MUTED)

    if report.blank_check is not None:
        bc = report.blank_check
        cursor.line("Заготовка", indent=0, bold=True)
        cursor.line(
            f"— {bc.blank_from_drawing or '—'}: {_STATUS_LABEL[bc.status]}",
            indent=16,
            color=_STATUS_COLOR[bc.status],
        )
        if bc.note:
            cursor.wrapped_line(f"— {bc.note}", indent=32, size=10, color=_COLOR_MUTED)

    if report.technical_requirement_checks:
        cursor.line("Технические требования", indent=0, bold=True)
        for tt in report.technical_requirement_checks:
            status_color = _COLOR_OK if tt.is_recognized else _COLOR_WARN
            category = tt.category or "не распознана"
            cursor.wrapped_line(
                f"— п.{tt.number}: {tt.text}",
                indent=16,
                size=10,
                color=status_color,
            )
            cursor.line(f"  категория: {category}", indent=32, size=9, color=_COLOR_MUTED)

    gost_checks = [
        check
        for check in report.gost_checks
        if check.status is not GostCheckStatus.NOT_APPLICABLE
    ]
    if gost_checks:
        cursor.line("Оформление по ГОСТ ЕСКД", indent=0, bold=True)
        for check in gost_checks:
            actual = f" — фактически: «{check.actual_value}»" if check.actual_value else ""
            cursor.wrapped_line(
                f"— {check.standard_designation}, п. {check.clause_number}: "
                f"{check.parameter_name}: {_GOST_STATUS_LABEL[check.status]}{actual}",
                indent=16,
                size=10,
                color=_GOST_STATUS_COLOR[check.status],
            )
            if check.note:
                cursor.wrapped_line(check.note, indent=32, size=9, color=_COLOR_MUTED)

    cursor.gap(10)
    cursor.line("Находки", size=13, bold=True)
    cursor.gap(4)
    if not report.findings:
        cursor.line("Значимых замечаний не выявлено.", indent=16, color=_COLOR_OK)
    for finding in report.findings:
        cursor.wrapped_line(
            f"[{finding.severity}] {finding.message}",
            indent=16,
            size=10,
            color=_SEVERITY_COLOR.get(finding.severity, _COLOR_TEXT),
        )

    if report.summary is not None:
        cursor.gap(10)
        cursor.line("Резюме", size=13, bold=True)
        source_label = "сгенерировано LLM" if report.summary.generated_by == "llm" else "шаблонный текст"
        cursor.line(f"({source_label})", indent=0, size=9, color=_COLOR_MUTED)
        cursor.gap(2)
        cursor.wrapped_line(report.summary.text, indent=0, size=10)

    cursor.finish()

    buffer = io.BytesIO()
    doc.save(buffer)
    doc.close()
    return buffer.getvalue()

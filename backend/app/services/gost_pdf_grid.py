"""Курсор для рисования табличных ГОСТ-бланков в PDF (Фаза 17) —
настоящая сетка ячеек (page.draw_line/draw_rect), а не текстовый список
построчно, как в app/services/kd_review_pdf_export.py.

Кириллица — тот же паттерн, что и в kd_review_pdf_export.py:
fitz.TextWriter с объектом fitz.Font('helv'), не Page.insert_text() по
имени шрифта (глифы вне latin1 не рисуются). Один TextWriter на цвет на
страницу (TextWriter.append() не принимает цвет построчно), заливка
всех writer'ов происходит при переходе на новую страницу или при
финализации документа.
"""

from __future__ import annotations

import io

import fitz

_PAGE_WIDTH, _PAGE_HEIGHT = fitz.paper_size("a4-l")  # альбомная ориентация — широкие графы формы
_MARGIN = 20
_COLOR_TEXT = (0.05, 0.05, 0.08)
_COLOR_MUTED = (0.45, 0.45, 0.5)
_COLOR_LINE = (0.2, 0.2, 0.25)


class GostTableCursor:
    """Рисует таблицу построчно в пределах заданных границ столбцов
    (col_x — список x-координат границ, len(col_x) == число столбцов + 1).
    При нехватке места на странице переходит на новую и заново рисует
    шапку таблицы, как форма 1 -> форма 1б в реальных маршрутных картах
    (см. БД НСИ Аддитив/Маршраутная карта пример оформления.pdf)."""

    def __init__(
        self,
        doc: fitz.Document,
        *,
        col_x: list[float],
        row_height: float = 16,
        header_labels: list[str] | None = None,
        title: str | None = None,
        gost_form: str | None = None,
    ) -> None:
        self._doc = doc
        self._col_x = col_x
        self._row_height = row_height
        self._header_labels = header_labels or []
        self._title = title
        self._gost_form = gost_form

        self._page = doc.new_page(width=_PAGE_WIDTH, height=_PAGE_HEIGHT)
        self._writers_by_color: dict[tuple, fitz.TextWriter] = {}
        self._regular_font = fitz.Font("helv")
        self._bold_font = fitz.Font("hebo")
        self._y = _MARGIN

        self._draw_page_title()
        if self._header_labels:
            self._draw_header_row()

    def _writer_for(self, color: tuple) -> fitz.TextWriter:
        if color not in self._writers_by_color:
            self._writers_by_color[color] = fitz.TextWriter(self._page.rect)
        return self._writers_by_color[color]

    def _flush_page(self) -> None:
        for color, writer in self._writers_by_color.items():
            writer.write_text(self._page, color=color)
        self._writers_by_color = {}

    def _new_page(self) -> None:
        self._flush_page()
        self._page = self._doc.new_page(width=_PAGE_WIDTH, height=_PAGE_HEIGHT)
        self._y = _MARGIN
        self._draw_page_title(continuation=True)
        if self._header_labels:
            self._draw_header_row()

    def _draw_page_title(self, *, continuation: bool = False) -> None:
        if self._gost_form:
            label = f"{self._gost_form}" + (" (продолжение)" if continuation else "")
            self._text(label, x=_PAGE_WIDTH - _MARGIN - 220, y=self._y, size=9, color=_COLOR_MUTED)
        if self._title and not continuation:
            self._text(self._title, x=_MARGIN, y=self._y + 12, size=13, bold=True)
            self._y += 26
        else:
            self._y += 16

    def _text(
        self, value: str, *, x: float, y: float, size: float = 9, bold: bool = False, color=_COLOR_TEXT
    ) -> None:
        font = self._bold_font if bold else self._regular_font
        self._writer_for(color).append((x, y), value, font=font, fontsize=size)

    def _fit_text(self, value: str, *, col_index: int, y: float, size: float = 8.5, bold=False, color=_COLOR_TEXT) -> None:
        """Пишет текст внутри столбца, обрезая по ширине ячейки (реальные
        поля техпроцесса иногда длиннее графы — обрезка честнее наложения
        текста на соседнюю ячейку)."""
        x0 = self._col_x[col_index] + 3
        max_width = self._col_x[col_index + 1] - self._col_x[col_index] - 6
        font = self._bold_font if bold else self._regular_font
        text = value
        while text and font.text_length(text, fontsize=size) > max_width:
            text = text[:-1]
        if text != value and len(text) > 1:
            text = text[:-1] + "…"
        self._text(text, x=x0, y=y, size=size, bold=bold, color=color)

    def _draw_row_lines(self, y_top: float, y_bottom: float) -> None:
        for x in self._col_x:
            self._page.draw_line((x, y_top), (x, y_bottom), color=_COLOR_LINE, width=0.6)
        self._page.draw_line(
            (self._col_x[0], y_bottom), (self._col_x[-1], y_bottom), color=_COLOR_LINE, width=0.6
        )

    def _draw_header_row(self) -> None:
        y_top = self._y
        y_bottom = y_top + self._row_height
        self._page.draw_line(
            (self._col_x[0], y_top), (self._col_x[-1], y_top), color=_COLOR_LINE, width=0.6
        )
        self._draw_row_lines(y_top, y_bottom)
        for i, label in enumerate(self._header_labels):
            self._fit_text(label, col_index=i, y=y_bottom - 5, size=8, bold=True, color=_COLOR_MUTED)
        self._y = y_bottom

    def add_row(self, values: list[str]) -> None:
        if self._y + self._row_height > _PAGE_HEIGHT - _MARGIN:
            self._new_page()
        y_top = self._y
        y_bottom = y_top + self._row_height
        self._draw_row_lines(y_top, y_bottom)
        for i, value in enumerate(values):
            if i >= len(self._col_x) - 1:
                break
            self._fit_text(value, col_index=i, y=y_bottom - 5)
        self._y = y_bottom

    def _add_note_line(self, text: str, *, size: float, bold: bool, indent: float) -> None:
        if self._y + 14 > _PAGE_HEIGHT - _MARGIN:
            self._new_page()
        self._text(text, x=_MARGIN + indent, y=self._y + 10, size=size, bold=bold)
        self._y += 14

    def add_note(self, text: str, *, size: float = 9, bold: bool = False, indent: float = 0) -> None:
        """Свободная строка вне табличной сетки (напр. технические
        требования под таблицей операций) — переносится по словам, если
        не влезает по ширине страницы (длинные source_note расчётов не
        должны обрезаться за правым краем листа)."""
        font = self._bold_font if bold else self._regular_font
        max_width = _PAGE_WIDTH - _MARGIN - (_MARGIN + indent)

        words = text.split(" ")
        current = ""
        for word in words:
            candidate = f"{current} {word}".strip()
            if font.text_length(candidate, fontsize=size) > max_width and current:
                self._add_note_line(current, size=size, bold=bold, indent=indent)
                current = word
            else:
                current = candidate
        if current:
            self._add_note_line(current, size=size, bold=bold, indent=indent)

    def gap(self, size: float = 8) -> None:
        self._y += size

    def start_table(self, header_labels: list[str], *, col_x: list[float] | None = None) -> None:
        """Начинает табличный блок в текущей позиции курсора (после
        произвольных add_note()) — шапка запоминается для повтора при
        переносе на новую страницу (форма 1 -> форма 1б)."""
        if col_x is not None:
            self._col_x = col_x
        self._header_labels = header_labels
        if self._y + self._row_height > _PAGE_HEIGHT - _MARGIN:
            self._new_page()
        else:
            self._draw_header_row()

    def finish(self) -> bytes:
        self._flush_page()
        buffer = io.BytesIO()
        self._doc.save(buffer)
        self._doc.close()
        return buffer.getvalue()

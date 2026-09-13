"""OCR-парсер сканированного чертежа (без текстового слоя PDF).

Решение по QUESTIONS.md (обновлено пользователем): не обязательно
реализовывать полноценную CRAFT+CRNN-архитектуру из статьи Белоусова —
достаточно рабочего результата. Используется готовая библиотека
Tesseract (offline, кроссплатформенная, есть под Windows и macOS) через
pytesseract — соответствует правилу ТЗ п.4: не делать своё ML-решение,
если задачу решает готовая библиотека.

Требует установленного бинаря tesseract с языковым пакетом rus
(на macOS: `brew install tesseract-lang`; на Windows — установщик
tesseract-ocr с выбором Russian при установке, либо ручная копия
rus.traineddata в tessdata). Это dev/deploy-time зависимость, не
рантайм-скачивание — соответствует офлайн-требованию ТЗ, если
языковые данные зафиксированы в дистрибутиве согласно ТЗ п.
"Всё скачанное фиксируется локально".

Качество распознавания заметно хуже, чем у текстового слоя (плотный
чертёжный шрифт, мелкие графы штампа) — рендер в высоком разрешении
(400 DPI) и бинаризация Отсу перед OCR ощутимо улучшают результат по
сравнению с прямым OCR цветного рендера при 300 DPI (проверено на
синтетическом "скане" реального fixture — без предобработки штамп не
распознавался вовсе, с предобработкой ключевые поля читаются). Это всё
равно эвристика на реальном изображении, а не гарантия — часть полей
на сложных чертежах может остаться нераспознанной, что ожидаемо для
OCR-пути и не считается багом парсера.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import fitz
import numpy as np
import pytesseract

import re
from dataclasses import replace

from app.domain.cad.drawing_model import DrawingModel
from app.domain.material_text import extract_material_from_blank_designation
from app.infrastructure.cad.stamp_extraction import (
    Line,
    extract_technical_requirements,
    extract_title_block,
)
from app.infrastructure.cad.stamp_cells import (
    find_material_cell,
    find_part_name_cell,
    find_scale_cell,
    read_stamp_cells,
    recognize_designation_cell,
    recognize_material_cell,
)
from app.infrastructure.cad.stamp_ocr import (
    recognize_designation,
    recognize_mass,
    recognize_material_row,
    recognize_scale,
    refine_part_name,
    _stamp_variants,
)
from app.infrastructure.cad.roughness_ocr import recognize_general_roughness
from app.infrastructure.cad.technical_requirements_ocr import (
    recognize_technical_requirements,
)

_RENDER_DPI = 400  # выше, чем для детекции видов — точность OCR зависит от разрешения
# Векторный чертёж без текстового слоя рендерится крупнее: детализация
# ничем не ограничена, а мелкий шрифт штампа при 400 DPI читается плохо.
# Проверено на реальном чертеже МВАУ: при 400 DPI строка материала не
# распознаётся, при ~600 DPI читается «Плита Д16 АТ … ГОСТ 17232-2023».
_VECTOR_RENDER_DPI = 600
# Доля листа, начиная с которой растр считается сканом самого листа, а не
# вставленной картинкой (подпись, логотип занимают единицы процентов).
_SCAN_COVERAGE_FRACTION = 0.5
_TESSERACT_LANG = "rus+eng"  # смешение кириллицы и латиницы в технической документации
# PSM 11 (разрозненный текст, без предположения об ориентации/структуре
# страницы) даёт больше распознанных слов на чертеже, чем PSM 6 (единый
# блок) или PSM 3 (авто-сегментация) — страница чертежа состоит из
# разбросанных по полю текстовых фрагментов (штамп, ТТ, размеры), а не
# из связного текстового документа.
_TESSERACT_CONFIG = "--psm 11"


class OcrDrawingParser:
    """Реализация IDrawingParser для сканов без текстового слоя."""

    def parse(self, file_path: Path) -> DrawingModel:
        document = fitz.open(file_path)
        try:
            page = document[0]
            raster_dpi = self._effective_raster_dpi(document, page)
            # Для скана поднимать зум выше исходного разрешения бесполезно —
            # деталей это не добавит; для вектора, наоборот, полезно.
            render_dpi = _RENDER_DPI if raster_dpi is not None else _VECTOR_RENDER_DPI
            zoom = render_dpi / 72
            pixmap = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), colorspace=fitz.csGRAY)
            gray = np.frombuffer(pixmap.samples, dtype=np.uint8).reshape(
                pixmap.height, pixmap.width
            )
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

            lines = self._ocr_lines(binary, zoom)
            raw_text = "\n".join(ln[4] for ln in lines)
            title_block = extract_title_block(lines, page.rect.width, page.rect.height)
            # Общий проход по листу теряет мелкий шрифт основной надписи:
            # он рассчитан на разрозненный текст всей страницы, а штамп —
            # плотная таблица. Достраиваем графы прицельным разбором с
            # увеличением и удалением линий разграфки.
            title_block = self._recover_title_block(title_block, page)
            requirements = extract_technical_requirements(
                lines,
                page.rect.width,
                page.rect.height,
                # На скане первые пункты могут не распознаться — не повод
                # терять остальные (см. докстроку функции).
                require_first_item=False,
            )
            # У векторных PDF без текстового слоя детализация не
            # ограничена разрешением скана. Размеченная пользователем
            # зона ТТ читается отдельным проходом как связный список.
            if raster_dpi is None:
                targeted_requirements = recognize_technical_requirements(page)
                if targeted_requirements:
                    requirements = targeted_requirements
            general_roughness = recognize_general_roughness(page)

            return DrawingModel(
                file_path=str(file_path),
                page_count=document.page_count,
                title_block=title_block,
                technical_requirements=requirements,
                raw_text=raw_text,
                source_kind="ocr",
                raster_dpi=raster_dpi,
                general_roughness=general_roughness,
            )
        finally:
            document.close()

    @staticmethod
    def _recover_title_block(title_block, page: fitz.Page):
        """Достраивает графы основной надписи прицельным разбором штампа.

        Заполняются только те графы, которые общий проход не прочитал:
        если поле уже распознано, оно не перезаписывается.

        Размеры материала, прочитанные со скана, НЕ используются как
        заготовка: OCR технического шрифта путает цифры (на реальном
        чертеже «35» читается как «55»), и подставить их в сверку
        типоразмеров значило бы выдать домысел за факт. Марка и ссылка
        на стандарт устойчивы — они и попадают в поле «Материал».
        """
        variants = _stamp_variants(page)
        updates: dict[str, str] = {}

        # Основной источник — покамерный разбор таблицы штампа: он читает
        # графу целиком, не смешивая её с соседними (см. stamp_cells).
        # Построчные проходы ниже остаются запасным путём.
        cells = read_stamp_cells(page)

        if not title_block.material and not title_block.blank_designation:
            # Ячейка даёт верную СТРУКТУРУ графы (профиль, марка,
            # стандарт), построчное голосование — более точные ЗНАКИ в
            # номере стандарта. Берём лучшее от обоих: если голосование
            # нашло материал, оно и выигрывает, иначе идёт разбор ячейки.
            row = (
                recognize_material_cell(page, cells)
                or recognize_material_row(page)
                or find_material_cell(cells)
            )
            material = extract_material_from_blank_designation(row) if row else None
            if material:
                updates["material"] = material
                # Покамерный проход даёт полную графу 3 и используется
                # для сверки толщины заготовки с сортаментом НСИ.
                if row and re.search(r"\d+(?:[xх×]\d+){1,2}", row):
                    updates["blank_designation"] = row

        # Обозначение КД по ГОСТ 2.201 содержит цифровые группы. Если
        # общий проход выдал строку без единой цифры («Tete»), это заведомо
        # не обозначение, и прицельный результат её заменяет.
        # Обозначение по ГОСТ 2.201 — это группы цифр через точки и дефис.
        # Короткая строка или строка без такой структуры («Tete», «12») —
        # заведомо не обозначение, её заменяет прицельный результат.
        current_designation = title_block.designation or ""
        looks_like_designation = bool(
            re.search(r"\d{3}[.\-]\d", current_designation)
        )
        if not looks_like_designation:
            designation = recognize_designation_cell(page, cells) or recognize_designation(
                page, variants
            )
            if designation:
                updates["designation"] = designation

        if not title_block.mass:
            mass = recognize_mass(page, variants)
            if mass:
                updates["mass"] = mass

        if not title_block.scale:
            scale = find_scale_cell(cells) or recognize_scale(page, variants)
            if scale:
                updates["scale"] = scale

        # Наименование найдено позиционно (это надёжнее, чем искать его
        # по тексту среди фамилий и подписей соседних граф), но общий OCR
        # мог подменить кириллицу латиницей в аббревиатуре.
        # Наименование: позиционный разбор общего прохода обычно точнее в
        # знаках, покамерный — надёжнее находит саму графу. Используем
        # покамерный, только если позиционный не дал результата или дал
        # его с латинскими подменами, которые не удалось исправить.
        refined = (
            refine_part_name(page, title_block.part_name)
            if title_block.part_name
            else None
        )
        if refined and not re.search(r"[A-Za-z]", refined):
            if refined != title_block.part_name:
                updates["part_name"] = refined
        else:
            cell_name = find_part_name_cell(cells)
            if cell_name:
                updates["part_name"] = cell_name
            elif refined and refined != title_block.part_name:
                updates["part_name"] = refined

        return replace(title_block, **updates) if updates else title_block

    @staticmethod
    def _effective_raster_dpi(document: fitz.Document, page: fitz.Page) -> float | None:
        """Разрешение растра, которым нарисован ЛИСТ, если чертёж — скан.

        Возвращает None для ВЕКТОРНЫХ чертежей без текстового слоя: там
        детализация не ограничена ничем, лист можно отрендерить в любом
        разрешении, и говорить о «DPI скана» бессмысленно.

        Ключевой момент — доля листа, которую растр реально закрывает.
        В векторном чертеже тоже бывают вставленные картинки (подпись,
        логотип на 5-6% листа): считать по ним DPI всего листа неверно —
        именно эта ошибка приводила к тому, что нормальные векторные
        чертежи объявлялись нечитаемыми сканами.
        """
        page_area = page.rect.width * page.rect.height
        if page_area <= 0:
            return None

        best_dpi: float | None = None
        for image in page.get_images(full=True):
            xref = image[0]
            placements = page.get_image_rects(xref)
            covered = max(
                ((r.width * r.height) / page_area for r in placements), default=0.0
            )
            # Растр считается «сканом листа», только если он закрывает
            # основную часть страницы.
            if covered < _SCAN_COVERAGE_FRACTION:
                continue
            try:
                pixmap = fitz.Pixmap(document, xref)
            except Exception:
                # Битый или неподдерживаемый объект изображения — не повод
                # ронять разбор чертежа целиком.
                continue
            for rect in placements:
                if rect.width <= 0 or rect.height <= 0:
                    continue
                # DPI относительно РАЗМЕЩЕНИЯ растра, а не всего листа.
                dpi = min(pixmap.width * 72 / rect.width, pixmap.height * 72 / rect.height)
                if best_dpi is None or dpi > best_dpi:
                    best_dpi = dpi
        return best_dpi

    def _ocr_lines(self, binary_image: np.ndarray, zoom: float) -> list[Line]:
        data = pytesseract.image_to_data(
            binary_image,
            lang=_TESSERACT_LANG,
            config=_TESSERACT_CONFIG,
            output_type=pytesseract.Output.DICT,
        )
        grouped: dict[tuple[int, int, int], list[int]] = {}
        for i, text in enumerate(data["text"]):
            if not text.strip():
                continue
            key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
            grouped.setdefault(key, []).append(i)

        lines: list[Line] = []
        for indices in grouped.values():
            words = [data["text"][i] for i in indices]
            x0 = min(data["left"][i] for i in indices) / zoom
            y0 = min(data["top"][i] for i in indices) / zoom
            x1 = max(data["left"][i] + data["width"][i] for i in indices) / zoom
            y1 = max(data["top"][i] + data["height"][i] for i in indices) / zoom
            lines.append((x0, y0, x1, y1, " ".join(words)))
        return lines

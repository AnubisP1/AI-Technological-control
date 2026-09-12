"""Прицельное распознавание основной надписи (ГОСТ 2.104) на чертежах
без текстового слоя.

Зачем отдельно от OcrDrawingParser: тот распознаёт ВЕСЬ лист одним
проходом с --psm 11 (разрозненный текст) — так находятся крупные
надписи и технические требования, но мелкий шрифт штампа теряется.
Основная надпись — это плотная таблица в углу листа, и она требует
своего режима: увеличенный фрагмент, удаление линий разграфки
(они дробят символы и сбивают Tesseract) и несколько попыток
распознавания с разными режимами сегментации.

Несколько попыток вместо одной «правильной» — потому что качество
чертежей разное, и режим, выигрывающий на одном, проигрывает на
другом (проверено на корпусе МВАУ). Результаты не усредняются:
из всех вариантов выбирается тот, который дал осмысленное значение
поля по правилам предметной области (см. _pick_material).
"""

from __future__ import annotations

import re
from collections import Counter

import cv2
import fitz
import numpy as np
import pytesseract

from app.domain.material_text import BLANK_PROFILE_ALTERNATION

# Доля листа, отводимая под основную надпись. Шире, чем STAMP_X_FRACTION
# в stamp_extraction: там координаты уже распознанных строк, здесь —
# грубая обрезка картинки, и лучше захватить лишнее, чем срезать графу.
_STAMP_X_FRACTION = 0.55
_STAMP_Y_FRACTION = 0.76

# Масштабы рендера фрагмента штампа. Больше — не всегда лучше: на
# крупном зуме Tesseract начинает дробить символы (проверено, на 8-10x
# результат хуже, чем на 5-6x).
_ZOOM_VARIANTS = (5, 6)
# psm 4 — колонки текста разной высоты, psm 6 — единый блок,
# psm 11 — разрозненный текст. На разных чертежах выигрывают разные.
_PSM_VARIANTS = (4, 6, 11)
_TESSERACT_LANG = "rus+eng"

# Часть графы 3 с профилем и маркой («Плита Д16 АТ 35x80x80»). Ссылку на
# стандарт ищем ОТДЕЛЬНО: в графе она обычно на второй строке, и требовать
# их рядом — значит не найти ничего (проверено на реальном чертеже).
_RE_PROFILE_PART = re.compile(
    rf"((?:{BLANK_PROFILE_ALTERNATION})\s+[A-ZА-ЯЁ0-9][^\n|]{{2,40}})",
    re.IGNORECASE,
)
_RE_GOST_PART = re.compile(r"ГОСТ\s*(\d{3,6}[\-–—]\d{2,4})", re.IGNORECASE)
# Хвост строки профиля: посторонние слова, попавшие из соседних граф
# («МАИ НИО 101», «Селин»). Отрезаются, чтобы не попасть в обозначение.
_RE_TRAILING_NOISE = re.compile(r"\s+(?:МА[ИЙM]|НИ[ОJ]|\|).*$", re.IGNORECASE)
# «Лист» — не только профиль сортамента, но и метка граф основной надписи
# («Лист», «Листов», «Лист N докум.»). Такие сочетания в графу 3 не идут.
_RE_SHEET_LABEL = re.compile(
    r"^Лист(?:ов)?\b\s*(?:Лист(?:ов)?|№|N|докум|\d+\s*$|$)", re.IGNORECASE
)
# В обозначении материала обязана быть марка — буквенно-цифровой токен
# вида «Д16», «Д16Т», «АМг2», «АД31». Без него это не графа 3.
_RE_HAS_GRADE = re.compile(r"[А-ЯЁA-Z]{1,3}\d{1,3}[А-ЯЁA-Z]?\b", re.IGNORECASE)


def _remove_table_lines(binary: np.ndarray) -> np.ndarray:
    """Убирает линии разграфки штампа, оставляя только текст.

    Линии графы примыкают к символам и заставляют Tesseract видеть
    вместо буквы «шум». Морфологическое открытие длинным горизонтальным
    и длинным вертикальным ядром выделяет именно линии (текст такой
    протяжённости не имеет), после чего они вычитаются из изображения.
    """
    inverted = 255 - binary
    height, width = inverted.shape
    horizontal = cv2.morphologyEx(
        inverted,
        cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_RECT, (max(width // 30, 15), 1)),
    )
    vertical = cv2.morphologyEx(
        inverted,
        cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(height // 15, 15))),
    )
    lines = cv2.dilate(
        cv2.bitwise_or(horizontal, vertical), np.ones((3, 3), np.uint8), iterations=1
    )
    return 255 - cv2.subtract(inverted, lines)


def _stamp_variants(page: fitz.Page) -> list[str]:
    """Все варианты распознавания фрагмента с основной надписью."""
    variants: list[str] = []
    for zoom in _ZOOM_VARIANTS:
        pixmap = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), colorspace=fitz.csGRAY)
        gray = np.frombuffer(pixmap.samples, dtype=np.uint8).reshape(
            pixmap.height, pixmap.width
        )
        crop = gray[
            int(pixmap.height * _STAMP_Y_FRACTION) :,
            int(pixmap.width * _STAMP_X_FRACTION) :,
        ]
        if crop.size == 0:
            continue
        _, binary = cv2.threshold(crop, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        for image in (binary, _remove_table_lines(binary)):
            for psm in _PSM_VARIANTS:
                try:
                    variants.append(
                        pytesseract.image_to_string(
                            image, lang=_TESSERACT_LANG, config=f"--psm {psm}"
                        )
                    )
                except Exception:
                    # Отдельный неудачный режим не должен ронять разбор.
                    continue
    return variants


# Частые подмены кириллицы латиницей и цифрами в OCR технического шрифта.
_CONFUSIONS = str.maketrans({"A": "А", "C": "С", "E": "Е", "O": "О", "P": "Р",
                             "T": "Т", "X": "Х", "H": "Н", "K": "К", "M": "М",
                             "B": "В", "y": "у", "$": "5", "S": "5", "l": "1"})


def _normalize_gost_word(text: str) -> str:
    """Приводит искажённые OCR написания «ГОСТ» к каноническому."""
    return re.sub(r"\b[ГГF][O0О][CСG][TТ]\b", "ГОСТ", text, flags=re.IGNORECASE)


def recognize_material_row(page: fitz.Page) -> str | None:
    """Строка графы 3 («Плита Д16 АТ 35x80x80 ГОСТ 17232-2023») со скана.

    Возвращает None, если ни один вариант распознавания не дал строки,
    похожей на обозначение материала/заготовки — выдумывать значение
    графы нельзя, лучше честно оставить поле нераспознанным.
    """
    profile_parts: list[str] = []
    gost_parts: list[str] = []

    for variant in _stamp_variants(page):
        normalized = _normalize_gost_word(variant.translate(_CONFUSIONS))
        for line in normalized.splitlines():
            profile_match = _RE_PROFILE_PART.search(line)
            if profile_match:
                cleaned = _RE_TRAILING_NOISE.sub("", profile_match.group(1))
                cleaned = re.sub(r"\s+", " ", cleaned).strip(" .,;|")
                if (
                    cleaned
                    and not _RE_SHEET_LABEL.match(cleaned)
                    and _RE_HAS_GRADE.search(cleaned)
                ):
                    profile_parts.append(cleaned)
            gost_match = _RE_GOST_PART.search(line)
            if gost_match:
                gost_parts.append(f"ГОСТ {gost_match.group(1)}")

    if not profile_parts:
        return None

    # Из нескольких прочтений берём самое частое: устойчивый результат
    # вероятнее верен, чем случайное искажение одного прохода.
    profile = max(set(profile_parts), key=lambda c: (profile_parts.count(c), -len(c)))
    if not gost_parts:
        return profile
    gost = max(set(gost_parts), key=gost_parts.count)
    return f"{profile} {gost}"


# ---------- Остальные графы основной надписи ----------

# Обозначение КД: «МВАУ.104759.001-01.111.020». OCR теряет и добавляет
# пробелы, путает «У»/«9», поэтому ищем структуру (буквенный префикс +
# длинная цепочка цифр с разделителями), а не точный шаблон.
# Буква «У» в префиксе («МВАУ») в чертёжном шрифте почти неотличима от
# цифры 9, и OCR регулярно уводит её в начало цифровой части. Поэтому
# префикс захватывается вместе с возможной «лишней» первой цифрой,
# а потом она отбрасывается по длине (см. _DESIGNATION_DIGITS).
# Ищем СТРУКТУРУ обозначения по ГОСТ 2.201 — шесть цифр кода организации,
# затем группы через точки и дефис. Разделители у OCR произвольные
# (точка, пробел, дефис, апостроф), поэтому между группами допускается
# любой из них. Префикс («МВАУ») ищется отдельно: он часто отрывается
# от цифр или теряет последнюю букву.
_RE_DESIGNATION = re.compile(
    r"(\d{3})[^\dА-Яа-яA-Za-z]{0,2}(\d{3})[^\d]{1,2}(\d{3})\s*[-–—]\s*(\d{2})"
    r"[^\d]{1,2}(\d{3})[^\d]{1,2}(\d{3})"
)
# Буквенный префикс обозначения («МВАУ») со скана НЕ восстанавливается.
# В чертёжном шрифте «У» почти неотличима от 9, а пробелы между буквами
# произвольны: реальные прочтения — «БА У», «МВА 9», «Bau», «84 9».
# Достоверно выбрать из них нельзя, а подставить правдоподобный —
# значит выдать догадку за распознанное значение. Возвращается только
# цифровая часть, которая читается устойчиво; префикс дописывает
# технолог. Ср. с массой и материалом, где голосование даёт однозначный
# результат и значение возвращается целиком.
# Число цифр в обозначении по ГОСТ 2.201: 6 + 3 + 2 + 3 + 3.
_DESIGNATION_DIGITS = 17
# Масса в графе 5: «82гр.», «82 г», «0,082». Единицу и точку в конце
# ГОСТ Р 2.104 не предусматривает — массу указывают числом в килограммах,
# поэтому запись «82гр.» нормализуется, а не переносится как есть.
_RE_MASS = re.compile(r"\b(\d{1,5}(?:[.,]\d{1,4})?)\s*(кг|г|гр)\.?(?=\s|$)", re.IGNORECASE)
# Масштаб: «1:1», «1.1» (OCR часто читает двоеточие как точку), «2:1».
_RE_SCALE = re.compile(r"\b([1-9]\d{0,2})\s*[:.,]\s*([1-9]\d{0,2})\b")


def _vote(values: list[str]) -> str | None:
    """Самое частое прочтение; при равенстве — более длинное."""
    if not values:
        return None
    return max(set(values), key=lambda v: (values.count(v), len(v)))


def recognize_designation(page: fitz.Page, variants: list[str] | None = None) -> str | None:
    """Цифровая часть обозначения КД из графы 2 («104759.001-01.111.020»).

    Цифры собираются голосованием по всем вариантам распознавания
    ПОРАЗРЯДНО: OCR ошибается в отдельных знаках, но редко в одних и тех
    же, поэтому поразрядное большинство устойчивее любого одного прохода.

    Буквенный префикс («МВАУ») намеренно НЕ возвращается — см.
    комментарий у _RE_DESIGNATION: со скана он не читается достоверно.
    """
    variants = variants if variants is not None else _stamp_variants(page)

    groups: list[tuple[str, ...]] = []
    for variant in variants:
        for line in variant.translate(_CONFUSIONS).splitlines():
            match = _RE_DESIGNATION.search(line)
            if match:
                groups.append(match.groups())

    if not groups:
        return None

    # Поразрядное голосование внутри каждой группы: OCR ошибается в
    # отдельных знаках, но редко в одних и тех же, поэтому большинство
    # по разряду устойчивее любого отдельного прохода.
    voted: list[str] = []
    for position in range(6):
        column = [g[position] for g in groups]
        counts = Counter(column)
        (best, best_count), *rest = counts.most_common()
        # Если два прочтения набрали поровну, достоверного значения нет.
        # Выбирать «любое» — значит выдать монетку за распознанный номер;
        # группа помечается вопросительными знаками, чтобы технолог сразу
        # видел, какие именно разряды нужно сверить с чертежом.
        if rest and rest[0][1] == best_count:
            voted.append("?" * len(best))
        else:
            voted.append(best)

    return f"{voted[0]}{voted[1]}.{voted[2]}-{voted[3]}.{voted[4]}.{voted[5]}"


def recognize_mass(page: fitz.Page, variants: list[str] | None = None) -> str | None:
    """Масса из графы 5, нормализованная по ГОСТ Р 2.104.

    Стандарт предписывает указывать массу в килограммах без единицы
    измерения. Чертёж может нести «82гр.» — это граммы с лишней точкой;
    приводим к «0,082», сохраняя десятичную запятую, принятую в КД.
    """
    variants = variants if variants is not None else _stamp_variants(page)

    values: list[str] = []
    for variant in variants:
        for line in variant.translate(_CONFUSIONS).splitlines():
            match = _RE_MASS.search(line)
            if not match:
                continue
            # Графа «Масса» в форме 1 стоит в одной строке с наименованием
            # изделия и масштабом. Одинокое число в стороне — чаще всего
            # размер с поля чертежа, а не масса, поэтому строке с
            # контекстом отдаётся предпочтение (вес голоса ниже).
            has_context = len(line.split()) >= 3
            raw = float(match.group(1).replace(",", "."))
            unit = match.group(2).lower()
            kilograms = raw / 1000 if unit in {"г", "гр"} else raw
            normalized = f"{kilograms:g}".replace(".", ",")
            values.append(normalized)
            if has_context:
                values.append(normalized)
    return _vote(values)


def recognize_scale(page: fitz.Page, variants: list[str] | None = None) -> str | None:
    """Масштаб из графы 6. OCR часто читает двоеточие как точку, поэтому
    разделитель распознаётся свободно, а возвращается канонический «1:1»."""
    variants = variants if variants is not None else _stamp_variants(page)

    values: list[str] = []
    for variant in variants:
        for line in variant.translate(_CONFUSIONS).splitlines():
            # Масштаб ищем рядом со словом-меткой, иначе поймаем размеры
            # с чертежа («1.4», «2.5» и т.п.).
            if "асштаб" not in line and "acштаб" not in line.lower():
                continue
            for numerator, denominator in _RE_SCALE.findall(line):
                values.append(f"{numerator}:{denominator}")
    return _vote(values)


# Графа 1 «Наименование изделия»: русский текст из букв, пробелов и
# дефисов. Цифры и латиница в наименовании детали не встречаются, но
# OCR подмешивает их из соседних граф — такие куски отсекаются.
_RE_PART_NAME = re.compile(r"([А-ЯЁ][а-яёА-ЯЁ]{3,}(?:\s+[А-Яа-яЁё\-]{2,}){0,5})")
# Слова соседних граф и подписей, попадающие в ту же строку.
_PART_NAME_STOP_WORDS = frozenset(
    {
        "лит", "лист", "листов", "масса", "масштаб", "формат", "копировал",
        "изм", "докум", "подп", "дата", "разраб", "пров", "контр", "утв",
        "плита", "лента", "круг", "пруток", "гост", "ост", "маи", "нио",
        "информация", "документ", "документе", "получатель", "изготовления",
    }
)


# Кириллический белый список: в наименовании изделия латиницы не бывает,
# и без него Tesseract подменяет «ОЧК» на «UYK»/«UGK» — визуально
# похожие латинские буквы. Со списком те же символы читаются верно.
# Дефис в конце списка Tesseract принимает за начало флага командной
# строки и падает с «unknown command line argument», поэтому список
# берётся в кавычки, а дефис ставится не последним символом.
_CYRILLIC_WHITELIST = (
    '-c tessedit_char_whitelist="'
    "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"
    "абвгдеёжзийклмнопрстуфхцчшщъыьэюя-"
    ' "'
)


def _cyrillic_stamp_words(page: fitz.Page) -> list[str]:
    """Строки штампа, распознанные только кириллицей.

    Пробелы Tesseract в этом режиме часто теряет, поэтому слова
    собираются из координат отдельных фрагментов, а не из готовой
    строки.
    """
    lines: list[str] = []
    for zoom in _ZOOM_VARIANTS:
        pixmap = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), colorspace=fitz.csGRAY)
        gray = np.frombuffer(pixmap.samples, dtype=np.uint8).reshape(
            pixmap.height, pixmap.width
        )
        crop = gray[
            int(pixmap.height * _STAMP_Y_FRACTION) :,
            int(pixmap.width * _STAMP_X_FRACTION) :,
        ]
        if crop.size == 0:
            continue
        _, binary = cv2.threshold(crop, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        for image in (binary, _remove_table_lines(binary)):
            for psm in _PSM_VARIANTS:
                try:
                    data = pytesseract.image_to_data(
                        image,
                        lang="rus",
                        config=f"--psm {psm} {_CYRILLIC_WHITELIST}",
                        output_type=pytesseract.Output.DICT,
                    )
                except Exception:
                    continue
                grouped: dict[tuple[int, int, int], list[str]] = {}
                for i, word in enumerate(data["text"]):
                    if not word.strip():
                        continue
                    key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
                    grouped.setdefault(key, []).append(word.strip())
                lines.extend(" ".join(words) for words in grouped.values())
    return lines


def refine_part_name(page: fitz.Page, part_name: str) -> str:
    """Исправляет латинские вставки в уже найденном наименовании.

    Позиционный разбор (stamp_extraction) находит наименование по месту в
    штампе — это надёжнее, чем угадывать его по тексту среди фамилий и
    подписей соседних граф. Но общий OCR подменяет кириллические буквы
    визуально похожими латинскими: «ОЧК» читается как «UYK», «UGK».
    Здесь тот же фрагмент перечитывается со списком допустимых символов
    (только кириллица) и латинский кусок заменяется прочитанным.

    Если кириллический проход не дал подходящей замены, наименование
    возвращается КАК ЕСТЬ: подставить правдоподобную аббревиатуру вместо
    нераспознанной значило бы выдумать содержимое чертежа.
    """
    latin_fragments = re.findall(r"[A-Za-z]{2,}", part_name)
    if not latin_fragments:
        return part_name

    cyrillic_lines = _cyrillic_stamp_words(page)
    refined = part_name
    for fragment in latin_fragments:
        # Ищем строку, где то же наименование прочитано кириллицей.
        prefix = part_name.split(fragment)[0].strip()
        anchor = prefix.split()[-1] if prefix.split() else ""
        if not anchor or len(anchor) < 4:
            continue
        for line in cyrillic_lines:
            position = line.lower().find(anchor.lower())
            if position < 0:
                continue
            # Пробелы в кириллическом проходе часто теряются
            # («КронштеиннавескиОЧК»), поэтому берём символы сразу за
            # якорем, а не «следующее слово».
            tail = line[position + len(anchor) :].lstrip(" -")
            candidate = tail[: len(fragment)]
            # Замена принимается, только если это столько же букв: та же
            # аббревиатура другим алфавитом, а не соседнее слово.
            if len(candidate) == len(fragment) and candidate.isalpha():
                refined = refined.replace(fragment, candidate.upper())
                break
    return refined

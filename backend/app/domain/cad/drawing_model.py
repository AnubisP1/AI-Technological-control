"""Доменные структуры результата разбора чертежа (PDF).

Модуль 1.1 по ТЗ: "извлечение данных с видов чертежа, технических
требований (ТТ) и основной надписи". См. также архитектуру распознавания
из статьи Белоусова (dev/docs/ARCHITECTURE.md, раздел "OCR и анализ
чертежа") — сначала используем встроенный текстовый слой PDF там, где он
есть (векторный чертёж), полноценный OCR (CRAFT+CRNN) нужен только для
сканов без текстового слоя, это отдельная будущая реализация того же
контракта.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class TitleBlockFields:
    """Поля основной надписи (ГОСТ 2.104) — то, что удалось распознать.
    Отсутствующее поле — None, не пустая строка (не выдумываем то, чего нет)."""

    designation: str | None = None  # обозначение детали, напр. 'К200-150-400ENERAL.20'
    part_name: str | None = None  # наименование, напр. 'Вал'
    material: str | None = None  # материал, напр. '45 ГОСТ 1050-2013'
    blank_designation: str | None = None  # заготовка, напр. 'Круг 67 ГОСТ 2590-2006'
    scale: str | None = None  # масштаб, напр. '1:2'
    sheet_format: str | None = None  # формат листа, напр. 'A3'
    mass: str | None = None


@dataclass(frozen=True)
class TechnicalRequirement:
    """Один пронумерованный пункт технических требований чертежа."""

    number: int
    text: str


@dataclass(frozen=True)
class GeneralRoughness:
    """Общее обозначение шероховатости из правого верхнего угла листа."""

    parameter: str  # Ra, Rz, Rmax и т. п.
    value_um: float
    raw_text: str
    # Длинная полка справа от знака. Она проверяется отдельно по
    # ГОСТ 2.309-73, п. 1.2, когда иных указаний кроме параметра нет.
    has_extended_shelf: bool


# Ниже этого разрешения строка основной надписи занимает считанные
# пиксели и не читается никаким OCR. Замерено на корпусе реальных
# чертежей: у скана 59 DPI на лист A1 строка штампа ~12 px, и попытки
# распознать её при рендере 400 и 800 DPI с апскейлом дают только
# крупный текст. Это предел разрешения исходника, а не качества движка.
LOW_DPI_THRESHOLD = 150.0


@dataclass(frozen=True)
class DrawingModel:
    file_path: str
    page_count: int
    title_block: TitleBlockFields
    technical_requirements: tuple[TechnicalRequirement, ...] = field(default_factory=tuple)
    raw_text: str = ""
    # Откуда взят текст: 'text_layer' — встроенный текстовый слой PDF,
    # 'ocr' — распознавание растра. Нужно, чтобы отличать «поле пустое
    # на чертеже» от «поле не прочитано из-за качества файла».
    source_kind: str = "text_layer"
    # Эффективное разрешение растра для сканов (точек на дюйм); None для
    # чертежей с текстовым слоем и для растров без вложенного изображения.
    raster_dpi: float | None = None
    general_roughness: GeneralRoughness | None = None

    @property
    def has_text_layer(self) -> bool:
        """False означает скан без встроенного текста — нужен полноценный OCR
        (CRAFT+CRNN), который на этой фазе не реализован, а не то, что
        текста на чертеже нет."""
        return len(self.raw_text.strip()) > 0

    @property
    def is_low_resolution_scan(self) -> bool:
        """Скан слишком низкого разрешения, чтобы основную надпись можно
        было прочитать в принципе. Отличать этот случай обязательно:
        иначе нераспознанный материал выглядит как «материал на чертеже
        не указан», хотя он указан и корректен."""
        return (
            self.source_kind == "ocr"
            and self.raster_dpi is not None
            and self.raster_dpi < LOW_DPI_THRESHOLD
        )

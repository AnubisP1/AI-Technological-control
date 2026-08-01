"""Сравнение фото изделия с эталоном через классическое CV (OpenCV) —
Модуль 3.1. Не нейросетевая модель — по правилу ТЗ п.4 (готовая
библиотека вместо собственного ML/CV там, где она решает задачу) и по
формулировке самого сценария: "не сравниваем точно по миллиметрам
геометрию, для демонстрации работы достаточно просто сравнить по фото".

Метод — сравнение силуэта (внешнего контура) детали на фото:
1. Оба фото сегментируются (grayscale + Otsu-бинаризация) — выделяется
   крупнейший контур, это и есть силуэт детали на фоне.
2. Силуэт нормализуется по площади (не по bounding box!) и центру масс —
   так сравнение устойчиво к масштабу/смещению кадра, а лишний/
   недостающий фрагмент детали не "прячется" в перерасчёте масштаба
   (bounding-box-нормализация именно так пряталась в прототипировании —
   см. dev/QUESTIONS.md).
3. Ищется лучший угол поворота (грубый перебор 0..345° с шагом 15°) —
   реальное фото не обязано быть снято в той же ориентации, что эталон.
4. Похожесть — IoU (пересечение/объединение) силуэтов после выравнивания.

Пороговые значения калибровались на реальных тестовых фото одной и той
же физической детали под разными ракурсами (см. PROGRESS.md, Фаза 6):
одинаковый ракурс даёт IoU ~0.90-0.97, разные ракурсы одной детали —
~0.63-0.71. Между этими диапазонами и ниже них система не пытается
угадать, а явно возвращает 'inconclusive' — не выдаёт "норма"/"брак" при
недостаточных основаниях (см. domain/quality_control/quality_model.py).

По решению пользователя (см. QUESTIONS.md) находки не пытаются
классифицировать конкретный тип дефекта (отверстие/фаска/выступ) — на
достигнутом уровне детализации силуэтного сравнения на реальных тестовых
фото это было бы избыточной точностью, которую метод не может подтвердить
(ложные срабатывания от обычного шума фото сопоставимы по размеру с
синтетическим тестовым дефектом). Отчёт даёт только общий вердикт и
метрику схожести.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from app.domain.quality_control.quality_model import PhotoComparisonResult, QualityVerdict

_WORK_SIZE = 300
_CANVAS_SIZE = 260
_TARGET_EQUIV_DIAMETER = 140.0
_ROTATION_STEP_DEGREES = 15

_IOU_OK_THRESHOLD = 0.80
_IOU_DEFECTIVE_THRESHOLD = 0.55


class SilhouetteNotFoundError(ValueError):
    pass


def _extract_silhouette(image_path: Path) -> tuple[np.ndarray, tuple[float, float], float]:
    image = cv2.imread(str(image_path))
    if image is None:
        raise SilhouetteNotFoundError(f"Не удалось прочитать изображение: {image_path}")

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, (_WORK_SIZE, _WORK_SIZE))
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        raise SilhouetteNotFoundError(
            f"На фото не найден силуэт детали на фоне: {image_path}"
        )

    largest = max(contours, key=cv2.contourArea)
    area = cv2.contourArea(largest)
    if area <= 0:
        raise SilhouetteNotFoundError(f"Найденный силуэт вырожден: {image_path}")

    mask = np.zeros((_WORK_SIZE, _WORK_SIZE), dtype=np.uint8)
    cv2.drawContours(mask, [largest], -1, 255, thickness=cv2.FILLED)

    moments = cv2.moments(largest)
    center = (moments["m10"] / moments["m00"], moments["m01"] / moments["m00"])
    return mask, center, area


def _normalize(mask: np.ndarray, center: tuple[float, float], area: float) -> np.ndarray:
    equivalent_diameter = 2 * np.sqrt(area / np.pi)
    scale = _TARGET_EQUIV_DIAMETER / equivalent_diameter

    transform = cv2.getRotationMatrix2D(center, angle=0, scale=scale)
    transform[0, 2] += _CANVAS_SIZE / 2 - center[0]
    transform[1, 2] += _CANVAS_SIZE / 2 - center[1]
    return cv2.warpAffine(mask, transform, (_CANVAS_SIZE, _CANVAS_SIZE))


def _iou(a: np.ndarray, b: np.ndarray) -> float:
    intersection = np.logical_and(a > 0, b > 0).sum()
    union = np.logical_or(a > 0, b > 0).sum()
    return float(intersection / union) if union else 0.0


def _best_rotation_alignment(reference: np.ndarray, actual: np.ndarray) -> tuple[float, np.ndarray]:
    center = (_CANVAS_SIZE / 2, _CANVAS_SIZE / 2)
    best_score = -1.0
    best_aligned = actual
    for angle in range(0, 360, _ROTATION_STEP_DEGREES):
        transform = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(actual, transform, (_CANVAS_SIZE, _CANVAS_SIZE))
        score = _iou(reference, rotated)
        if score > best_score:
            best_score, best_aligned = score, rotated
    return best_score, best_aligned


class OpenCvPhotoComparator:
    """Реализация IPhotoComparator поверх OpenCV (см. модуль docstring)."""

    def compare(self, reference_path: Path, actual_path: Path) -> PhotoComparisonResult:
        try:
            ref_mask, ref_center, ref_area = _extract_silhouette(reference_path)
            actual_mask, actual_center, actual_area = _extract_silhouette(actual_path)
        except SilhouetteNotFoundError as exc:
            return PhotoComparisonResult(
                verdict=QualityVerdict.INCONCLUSIVE,
                similarity_score=0.0,
                notes=(str(exc),),
            )

        ref_norm = _normalize(ref_mask, ref_center, ref_area)
        actual_norm = _normalize(actual_mask, actual_center, actual_area)

        similarity, _ = _best_rotation_alignment(ref_norm, actual_norm)

        if similarity >= _IOU_OK_THRESHOLD:
            verdict = QualityVerdict.OK
            notes = ("Силуэт изделия на фото соответствует эталону в пределах демонстрационной точности сравнения.",)
        elif similarity < _IOU_DEFECTIVE_THRESHOLD:
            verdict = QualityVerdict.DEFECTIVE
            notes = (
                "Силуэт изделия на фото заметно отличается от эталона — возможны лишние "
                "или недостающие элементы геометрии (отверстия/фаски/выступы). Точная "
                "локализация и тип отклонения не определяются данным методом сравнения "
                "по фото, требуется проверка технологом.",
            )
        else:
            verdict = QualityVerdict.INCONCLUSIVE
            notes = (
                "Схожесть силуэта в пограничном диапазоне — на реальных тестовых фото "
                "такой уровень нередко объясняется просто разницей ракурса съёмки, а не "
                "браком. Метод не может дать уверенный вердикт — требуется повторное фото "
                "или проверка технологом.",
            )

        return PhotoComparisonResult(
            verdict=verdict, similarity_score=round(similarity, 4), notes=notes
        )

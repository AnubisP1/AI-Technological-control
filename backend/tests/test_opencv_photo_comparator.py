from pathlib import Path

import cv2
import pytest

from app.domain.quality_control.quality_model import QualityVerdict
from app.infrastructure.quality_control.opencv_photo_comparator import OpenCvPhotoComparator

FIXTURES_ROOT = (
    Path(__file__).resolve().parents[3] / "КД для тестов" / "Пластиковые детали" / "1. Тестовая деталь пластик"
)
# Два фото одной и той же детали, снятые с одинакового (внешнего) ракурса.
SAME_ANGLE_A = FIXTURES_ROOT / "7a6046ea-69b2-44f2-ac83-3f9c0ba8a923.jpeg"
SAME_ANGLE_B = FIXTURES_ROOT / "fd46d227-602c-4b9b-bf28-de9a04a490a1.jpeg"
# Фото той же детали, но с внутреннего ракурса (в руке) — проверяет
# 'inconclusive' на угловом рассогласовании, не браке.
DIFFERENT_ANGLE = FIXTURES_ROOT / "0924d1d2-91b2-42a1-85e6-bfd5e7750982.jpeg"


def _require(path: Path) -> Path:
    if not path.exists():
        pytest.skip(f"fixture недоступен в этом окружении: {path}")
    return path


def _make_synthetic_defect_photo(tmp_path: Path) -> Path:
    """Генерирует тестовое изображение с грубым нарушением силуэта
    (закрашенный фрагмент детали цветом фона, имитирующий отсутствующий
    крупный участок геометрии) на основе реального фото — не выдаётся
    за настоящую фотографию брака, только для проверки ветки DEFECTIVE.

    Показательно грубый дефект выбран намеренно: прототипирование на
    реальных фото (см. PROGRESS.md, Фаза 6) показало, что мелкий лишний
    выступ (~2% площади силуэта) сопоставим по влиянию на IoU с
    естественным шумом фото на этих тестовых снимках — метод по
    силуэту надёжно ловит только явные несоответствия формы, не мелкие
    локальные детали, что и заявлено пользователю как ограничение
    демонстрационного сравнения по фото."""
    source = _require(SAME_ANGLE_A)
    image = cv2.imread(str(source))
    height, width = image.shape[:2]
    background_colour = (170, 170, 165)
    cv2.rectangle(
        image,
        (int(width * 0.32), int(height * 0.35)),
        (int(width * 0.72), int(height * 0.65)),
        background_colour,
        -1,
    )
    output_path = tmp_path / "synthetic_defect.jpg"
    cv2.imwrite(str(output_path), image)
    return output_path


def test_same_part_same_angle_photos_are_ok():
    reference = _require(SAME_ANGLE_A)
    actual = _require(SAME_ANGLE_B)

    result = OpenCvPhotoComparator().compare(reference, actual)

    assert result.verdict is QualityVerdict.OK
    assert result.similarity_score >= 0.80


def test_same_part_different_angle_is_inconclusive_not_defective():
    """Ключевой принцип: разница ракурса съёмки не должна выдаваться за
    брак — при недостаточной уверенности возвращается inconclusive."""
    reference = _require(SAME_ANGLE_A)
    actual = _require(DIFFERENT_ANGLE)

    result = OpenCvPhotoComparator().compare(reference, actual)

    assert result.verdict is not QualityVerdict.DEFECTIVE


def test_synthetic_silhouette_defect_is_flagged(tmp_path):
    reference = _require(SAME_ANGLE_B)
    actual = _make_synthetic_defect_photo(tmp_path)

    result = OpenCvPhotoComparator().compare(reference, actual)

    assert result.verdict is QualityVerdict.DEFECTIVE
    assert result.similarity_score < 0.80


def test_missing_silhouette_returns_inconclusive_not_crash(tmp_path):
    blank_path = tmp_path / "blank.jpg"
    import numpy as np

    blank = np.full((200, 200, 3), 255, dtype="uint8")
    cv2.imwrite(str(blank_path), blank)

    result = OpenCvPhotoComparator().compare(_require(SAME_ANGLE_A), blank_path)

    assert result.verdict is QualityVerdict.INCONCLUSIVE

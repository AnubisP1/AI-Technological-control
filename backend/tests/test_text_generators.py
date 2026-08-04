from pathlib import Path
from unittest.mock import patch

from app.domain.kd_review.text_generator_port import GeneratedText
from app.infrastructure.llm.qwen_text_generator import QwenTextGenerator
from app.infrastructure.llm.template_text_generator import TemplateTextGenerator


def test_template_generator_no_findings():
    generator = TemplateTextGenerator()
    result = generator.summarize_review(facts={"findings": []})

    assert result.generated_by == "template"
    assert "не выявлено" in result.text


def test_template_generator_lists_findings_with_severity_labels():
    generator = TemplateTextGenerator()
    facts = {
        "findings": [
            {"severity": "blocking", "message": "Материал не найден"},
            {"severity": "info", "message": "Пункт 3 не распознан"},
        ]
    }

    result = generator.summarize_review(facts=facts)

    assert result.generated_by == "template"
    assert "Материал не найден" in result.text
    assert "Пункт 3 не распознан" in result.text
    assert "Критично" in result.text


def test_template_generator_ignores_extra_facts_keys():
    """Регрессия: facts теперь несёт matched_material/candidate_materials
    (Фаза 18, для QwenTextGenerator) — шаблонный генератор не должен
    падать на незнакомых ключах, только на findings ориентируется."""
    generator = TemplateTextGenerator()
    facts = {
        "findings": [],
        "matched_material": {"grade": "Сталь 45", "gost_standard": "ГОСТ 1050-2013"},
        "candidate_materials": [{"grade": "Сталь 45", "gost_standard": "ГОСТ 1050-2013"}],
    }

    result = generator.summarize_review(facts=facts)
    assert result.generated_by == "template"


def test_qwen_generator_calls_engine_with_full_material_context():
    """QwenTextGenerator должен передать движку системный промпт и
    полный список кандидатных материалов (не только выбранный) — это
    ключевое отличие от прежней YandexGPT-реализации, добавленное по
    прямому запросу пользователя (Фаза 18): LLM должна видеть все
    материалы с их свойствами, чтобы реально предложить аналог."""
    generator = QwenTextGenerator(model_path=Path("/fake/model.gguf"), context_size=4096)

    facts = {
        "findings": [{"severity": "warning", "message": "Материал частично совпадает"}],
        "matched_material": {"grade": "40Х", "gost_standard": "ГОСТ 4543-2016"},
        "candidate_materials": [
            {
                "grade": "40Х",
                "gost_standard": "ГОСТ 4543-2016",
                "density_kg_m3": 7820,
                "tensile_strength_mpa": 730,
                "hardness_hb": 217,
                "machinability_index": 0.8,
            },
            {
                "grade": "12ХН3А",
                "gost_standard": "ГОСТ 4543-2016",
                "density_kg_m3": 7850,
                "tensile_strength_mpa": 950,
                "hardness_hb": 269,
                "machinability_index": 0.75,
            },
        ],
    }

    fake_engine = _FakeEngine("Связный анализ технологичности.")
    with patch("app.infrastructure.llm.qwen_text_generator.get_engine", return_value=fake_engine):
        result = generator.summarize_review(facts=facts)

    assert result == GeneratedText(text="Связный анализ технологичности.", generated_by="llm")
    assert "40Х" in fake_engine.last_user_prompt
    assert "12ХН3А" in fake_engine.last_user_prompt
    assert "0.8" in fake_engine.last_user_prompt
    assert "0.75" in fake_engine.last_user_prompt
    assert "Материал частично совпадает" in fake_engine.last_user_prompt


def test_qwen_generator_propagates_engine_errors_for_caller_fallback():
    """QwenTextGenerator сам не глотает ошибки — откат на шаблон делает
    вызывающий код (KdReviewService._summarize), как и раньше с YandexGPT."""
    generator = QwenTextGenerator(model_path=Path("/fake/model.gguf"), context_size=4096)

    with patch(
        "app.infrastructure.llm.qwen_text_generator.get_engine",
        side_effect=RuntimeError("модель не загружена"),
    ):
        try:
            generator.summarize_review(facts={"findings": []})
            assert False, "ожидалось исключение"
        except RuntimeError:
            pass


class _FakeEngine:
    def __init__(self, response_text: str) -> None:
        self._response_text = response_text
        self.last_user_prompt: str | None = None

    def complete(self, *, system_prompt: str, user_prompt: str, max_tokens: int, temperature: float) -> str:
        self.last_user_prompt = user_prompt
        return self._response_text

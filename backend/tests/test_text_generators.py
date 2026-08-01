import json
from unittest.mock import patch

import pytest

from app.domain.kd_review.text_generator_port import GeneratedText
from app.infrastructure.llm.template_text_generator import TemplateTextGenerator
from app.infrastructure.llm.yandex_gpt_text_generator import (
    YandexGptApiError,
    YandexGptTextGenerator,
)


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


def _mock_urlopen_response(payload: dict):
    class _Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps(payload).encode("utf-8")

    return _Response()


def test_yandex_gpt_generator_parses_successful_response():
    generator = YandexGptTextGenerator(api_key="test-key", folder_id="test-folder")
    fake_response = {
        "result": {"alternatives": [{"message": {"text": "Связный текст резюме."}}]}
    }

    with patch("urllib.request.urlopen", return_value=_mock_urlopen_response(fake_response)):
        result = generator.summarize_review(facts={"findings": []})

    assert result.generated_by == "llm"
    assert result.text == "Связный текст резюме."


def test_yandex_gpt_generator_raises_on_unexpected_response_shape():
    generator = YandexGptTextGenerator(api_key="test-key", folder_id="test-folder")

    with patch("urllib.request.urlopen", return_value=_mock_urlopen_response({"unexpected": True})):
        with pytest.raises(YandexGptApiError):
            generator.summarize_review(facts={"findings": []})


def test_yandex_gpt_generator_raises_on_network_error():
    import urllib.error

    generator = YandexGptTextGenerator(api_key="test-key", folder_id="test-folder")

    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("нет сети")):
        with pytest.raises(YandexGptApiError):
            generator.summarize_review(facts={"findings": []})

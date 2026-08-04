import json
from unittest.mock import patch

import pytest

from app.infrastructure.llm.polza_chat_responder import PolzaApiError as PolzaChatApiError
from app.infrastructure.llm.polza_chat_responder import PolzaChatResponder
from app.infrastructure.llm.polza_text_generator import PolzaApiError as PolzaTextApiError
from app.infrastructure.llm.polza_text_generator import PolzaTextGenerator


def _mock_urlopen_response(payload: dict):
    class _Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps(payload).encode("utf-8")

    return _Response()


def test_polza_text_generator_parses_successful_response():
    generator = PolzaTextGenerator(api_key="test-key")
    fake_response = {"choices": [{"message": {"content": "Связный анализ технологичности."}}]}

    with patch("urllib.request.urlopen", return_value=_mock_urlopen_response(fake_response)):
        result = generator.summarize_review(facts={"findings": [], "candidate_materials": []})

    assert result.generated_by == "llm"
    assert result.text == "Связный анализ технологичности."


def test_polza_text_generator_raises_on_unexpected_response_shape():
    generator = PolzaTextGenerator(api_key="test-key")

    with patch("urllib.request.urlopen", return_value=_mock_urlopen_response({"unexpected": True})):
        with pytest.raises(PolzaTextApiError):
            generator.summarize_review(facts={"findings": [], "candidate_materials": []})


def test_polza_text_generator_raises_on_network_error():
    import urllib.error

    generator = PolzaTextGenerator(api_key="test-key")

    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("нет сети")):
        with pytest.raises(PolzaTextApiError):
            generator.summarize_review(facts={"findings": [], "candidate_materials": []})


def test_polza_chat_responder_parses_successful_response():
    responder = PolzaChatResponder(api_key="test-key")
    fake_response = {"choices": [{"message": {"content": "Сталь 45 найдена в справочнике."}}]}

    with patch("urllib.request.urlopen", return_value=_mock_urlopen_response(fake_response)):
        result = responder.reply(question="Сталь 45", context_facts={"matches": []})

    assert result.generated_by == "llm"
    assert result.text == "Сталь 45 найдена в справочнике."


def test_polza_chat_responder_raises_on_network_error():
    import urllib.error

    responder = PolzaChatResponder(api_key="test-key")

    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("нет сети")):
        with pytest.raises(PolzaChatApiError):
            responder.reply(question="вопрос", context_facts={"matches": []})

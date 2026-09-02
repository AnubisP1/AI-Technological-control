from pathlib import Path

import pytest

from app.domain.assistant.chat_responder_port import ChatReply
from app.infrastructure.db.nsi_db import NsiDatabase, build_database
from app.services.assistant_service import AssistantService


def _service(tmp_path: Path, chat_responder=None, web_search_responder=None) -> AssistantService:
    metal_path = tmp_path / "metal.sqlite"
    additive_path = tmp_path / "additive.sqlite"
    build_database(NsiDatabase.METAL, metal_path)
    build_database(NsiDatabase.ADDITIVE, additive_path)
    return AssistantService(
        metal_path,
        additive_path,
        chat_responder=chat_responder,
        web_search_responder=web_search_responder,
    )


def test_ask_finds_real_material_and_falls_back_to_template(tmp_path: Path):
    service = _service(tmp_path)
    reply = service.ask("Расскажи про материал 12ХН3А")

    assert reply.generated_by == "template"
    assert "12ХН3А" in reply.text


def test_ask_finds_real_equipment_by_model_name(tmp_path: Path):
    service = _service(tmp_path)
    reply = service.ask("Какие есть станки 16К20?")

    assert reply.generated_by == "template"
    assert "16К20" in reply.text


def test_ask_with_no_matches_returns_helpful_message_not_hallucination(tmp_path: Path):
    service = _service(tmp_path)
    reply = service.ask("Расскажи про зюзюкин Ы-9000 кварзоплетень")

    assert reply.generated_by == "template"
    assert "не найдено" in reply.text.lower()


def test_ask_uses_llm_responder_when_available(tmp_path: Path):
    class _StubResponder:
        def reply(self, *, question: str, context_facts: dict) -> ChatReply:
            return ChatReply(text="ответ от LLM", generated_by="llm")

    service = _service(tmp_path, chat_responder=_StubResponder())
    reply = service.ask("Сталь 45")

    assert reply == ChatReply(text="ответ от LLM", generated_by="llm")


def test_ask_falls_back_to_template_when_llm_raises(tmp_path: Path):
    class _FailingResponder:
        def reply(self, *, question: str, context_facts: dict) -> ChatReply:
            raise RuntimeError("сеть недоступна")

    service = _service(tmp_path, chat_responder=_FailingResponder())
    reply = service.ask("Сталь 45")

    assert reply.generated_by == "template"
    assert "Сталь 45" in reply.text


def test_ask_finds_matches_for_inflected_russian_word_forms(tmp_path: Path):
    """Регрессия: реальный вопрос с падежными окончаниями ("марки",
    "стали") не находил ничего в keyword-поиске, хотя точно то же
    слово в словарной форме ("сталь") находило — найдено визуальной
    Playwright-проверкой демо-подсказок чата (Фаза 17, часть 6)."""
    service = _service(tmp_path)

    reply = service.ask("Какие марки стали есть в базе?")
    assert reply.generated_by == "template"
    assert "не найдено" not in reply.text.lower()
    assert "Сталь 45" in reply.text

    reply2 = service.ask("Какой материал подходит для пропеллера дрона?")
    assert reply2.generated_by == "template"
    assert "не найдено" not in reply2.text.lower()
    assert "PROPELLER" in reply2.text


def test_ask_uses_web_search_when_nsi_finds_nothing(tmp_path: Path):
    """Фаза 21, dev/QUESTIONS.md №18: если keyword-поиск по НСИ не нашёл
    вообще ничего (matches пуст), ассистент обязан попробовать
    web_search_responder перед откатом на шаблон "не найдено"."""

    class _StubWebSearchResponder:
        def reply(self, *, question: str, context_facts: dict) -> ChatReply:
            assert context_facts["matches"] == []
            return ChatReply(text="ответ из интернета", generated_by="llm")

    service = _service(tmp_path, web_search_responder=_StubWebSearchResponder())
    reply = service.ask("зюзюкин Ы-9000 кварзоплетень")

    assert reply == ChatReply(text="ответ из интернета", generated_by="llm")


def test_ask_does_not_use_web_search_when_nsi_finds_matches(tmp_path: Path):
    """Веб-поиск не должен подменять реальные найденные факты НСИ, даже
    если основной chat_responder не настроен (только шаблон) — это
    предотвращает ситуацию, когда модель предпочла бы интернет уже
    найденным локальным данным."""

    class _WebSearchResponderThatShouldNotBeCalled:
        def reply(self, *, question: str, context_facts: dict) -> ChatReply:
            raise AssertionError("веб-поиск не должен вызываться, когда НСИ нашла совпадения")

    service = _service(
        tmp_path, web_search_responder=_WebSearchResponderThatShouldNotBeCalled()
    )
    reply = service.ask("Сталь 45")

    assert reply.generated_by == "template"
    assert "Сталь 45" in reply.text


def test_ask_prefers_web_search_over_chat_responder_when_nsi_finds_nothing(tmp_path: Path):
    """Регрессия найдена на живом сервере: обычный chat_responder с
    антигаллюцинационным промптом при пустых matches УСПЕШНО отвечает
    "не найдено в НСИ" — это не исключение, поэтому если веб-поиск
    проверялся бы только внутри except основного chat_responder, он бы
    никогда не вызывался. Веб-поиск обязан пробоваться ПЕРВЫМ при пустых
    matches, до обычного chat_responder, а не только как запасной путь
    на случай сетевой ошибки."""

    class _StubChatResponderThatHonestlySaysNotFound:
        def reply(self, *, question: str, context_facts: dict) -> ChatReply:
            return ChatReply(text="В базе НСИ информация не найдена.", generated_by="llm")

    class _StubWebSearchResponder:
        def reply(self, *, question: str, context_facts: dict) -> ChatReply:
            return ChatReply(text="ответ из интернета", generated_by="llm")

    service = _service(
        tmp_path,
        chat_responder=_StubChatResponderThatHonestlySaysNotFound(),
        web_search_responder=_StubWebSearchResponder(),
    )
    reply = service.ask("зюзюкин Ы-9000 кварзоплетень")

    assert reply == ChatReply(text="ответ из интернета", generated_by="llm")


def test_ask_falls_back_to_template_when_web_search_raises(tmp_path: Path):
    class _FailingWebSearchResponder:
        def reply(self, *, question: str, context_facts: dict) -> ChatReply:
            raise RuntimeError("веб-поиск недоступен")

    service = _service(tmp_path, web_search_responder=_FailingWebSearchResponder())
    reply = service.ask("зюзюкин Ы-9000 кварзоплетень")

    assert reply.generated_by == "template"
    assert "не найдено" in reply.text.lower()


def test_search_table_query_is_not_vulnerable_to_sql_injection_via_question(tmp_path: Path):
    service = _service(tmp_path)
    # Ключевые слова вопроса всегда идут как bind-параметры LIKE, не
    # интерполируются в SQL — попытка инъекции просто не найдёт совпадений.
    reply = service.ask("материал'; DROP TABLE material;--")
    assert reply.generated_by == "template"

    # база должна остаться работоспособной
    reply2 = service.ask("Сталь 45")
    assert "Сталь 45" in reply2.text

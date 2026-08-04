import pytest

from app.domain.assistant.chat_responder_port import ChatReply
from app.domain.kd_review.text_generator_port import GeneratedText
from app.infrastructure.llm.chained_chat_responder import ChainedChatResponder
from app.infrastructure.llm.chained_text_generator import ChainedTextGenerator


class _FailingTextGenerator:
    def summarize_review(self, *, facts: dict) -> GeneratedText:
        raise RuntimeError("провайдер недоступен")


class _WorkingTextGenerator:
    def summarize_review(self, *, facts: dict) -> GeneratedText:
        return GeneratedText(text="ответ рабочего провайдера", generated_by="llm")


class _FailingChatResponder:
    def reply(self, *, question: str, context_facts: dict) -> ChatReply:
        raise RuntimeError("провайдер недоступен")


class _WorkingChatResponder:
    def reply(self, *, question: str, context_facts: dict) -> ChatReply:
        return ChatReply(text="ответ рабочего провайдера", generated_by="llm")


def test_chained_text_generator_uses_first_working_provider():
    chain = ChainedTextGenerator((_WorkingTextGenerator(), _FailingTextGenerator()))
    result = chain.summarize_review(facts={"findings": []})
    assert result.text == "ответ рабочего провайдера"


def test_chained_text_generator_falls_through_to_second_provider_on_first_failure():
    """Ключевой сценарий Фазы 18, часть 2: Polza.ai (первый) недоступен —
    переход на локальный Qwen (второй), не сразу на шаблон."""
    chain = ChainedTextGenerator((_FailingTextGenerator(), _WorkingTextGenerator()))
    result = chain.summarize_review(facts={"findings": []})
    assert result.text == "ответ рабочего провайдера"


def test_chained_text_generator_raises_last_error_when_all_providers_fail():
    """KdReviewService._summarize() ловит это исключение и откатывается
    на TemplateTextGenerator — цепочка сама не подменяет шаблонный путь."""
    chain = ChainedTextGenerator((_FailingTextGenerator(), _FailingTextGenerator()))
    with pytest.raises(RuntimeError, match="провайдер недоступен"):
        chain.summarize_review(facts={"findings": []})


def test_chained_text_generator_requires_at_least_one_provider():
    with pytest.raises(ValueError):
        ChainedTextGenerator(())


def test_chained_chat_responder_falls_through_on_first_failure():
    chain = ChainedChatResponder((_FailingChatResponder(), _WorkingChatResponder()))
    result = chain.reply(question="вопрос", context_facts={"matches": []})
    assert result.text == "ответ рабочего провайдера"


def test_chained_chat_responder_raises_last_error_when_all_providers_fail():
    chain = ChainedChatResponder((_FailingChatResponder(), _FailingChatResponder()))
    with pytest.raises(RuntimeError, match="провайдер недоступен"):
        chain.reply(question="вопрос", context_facts={"matches": []})

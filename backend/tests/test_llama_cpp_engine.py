from pathlib import Path

import pytest

from app.infrastructure.config import get_settings
from app.infrastructure.llm.llama_cpp_engine import LlamaModelUnavailableError, get_engine


def _require_llama_model() -> Path:
    model_path = get_settings().llama_model_path
    if model_path is None or not model_path.exists():
        pytest.skip("LLAMA_MODEL_PATH не настроен в этом окружении — локальная модель недоступна")
    return model_path


def test_get_engine_raises_clear_error_for_missing_model_file(tmp_path: Path):
    fake_path = tmp_path / "does-not-exist.gguf"
    with pytest.raises(LlamaModelUnavailableError):
        get_engine(fake_path, context_size=4096)


def test_get_engine_loads_real_model_and_completes_a_simple_prompt():
    """Реальный вызов модели — не мок. Проверяет только, что движок
    загружается и возвращает непустой связный текст, не конкретные
    формулировки (LLM недетерминирован по формулировкам, но не по факту
    успешного ответа)."""
    model_path = _require_llama_model()
    engine = get_engine(model_path, context_size=get_settings().llama_context_size)

    result = engine.complete(
        system_prompt="Отвечай одним словом на русском языке.",
        user_prompt="Как называется столица России?",
        max_tokens=20,
        temperature=0.0,
    )

    assert isinstance(result, str)
    assert len(result.strip()) > 0

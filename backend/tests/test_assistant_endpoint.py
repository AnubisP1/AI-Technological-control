from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_ask_assistant_endpoint_returns_real_material_match():
    # generated_by зависит от окружения (llm, если в .env настроен реальный
    # LLM-провайдер — Polza.ai/локальный Qwen, Фаза 18, часть 2; иначе
    # template) — само содержимое ответа обязано быть верным в обоих случаях.
    response = client.post("/assistant/chat", json={"question": "Сталь 45"})
    assert response.status_code == 200
    body = response.json()
    assert body["generated_by"] in ("template", "llm")
    assert "Сталь 45" in body["text"]


def test_ask_assistant_endpoint_handles_no_matches_without_hallucinating():
    # Точная формулировка отличается между шаблоном ("не найдено") и LLM
    # (может сказать "не найдена"/"не обнаружено" и т.д.) — проверяем сам
    # факт честного отказа (общий корень "найд"), не буквальную фразу.
    response = client.post("/assistant/chat", json={"question": "зюзюкин Ы-9000 кварзоплетень"})
    assert response.status_code == 200
    body = response.json()
    assert "найд" in body["text"].lower()


def test_ask_assistant_endpoint_rejects_missing_question_field():
    response = client.post("/assistant/chat", json={})
    assert response.status_code == 422

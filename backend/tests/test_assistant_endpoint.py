from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_ask_assistant_endpoint_returns_real_material_match():
    # generated_by зависит от окружения (llm, если в .env настроен
    # LLM-провайдер — локальный Qwen (llama.cpp); иначе template) —
    # само содержимое ответа обязано быть верным в обоих случаях.
    response = client.post("/assistant/chat", json={"question": "Сталь 45"})
    assert response.status_code == 200
    body = response.json()
    assert body["generated_by"] in ("template", "llm")
    # Марка проверяется по корню "стал" + номеру, а не буквальной строкой
    # "Сталь 45": падеж выбирает модель — локальный Qwen отвечает
    # "информация о стали 45", что так же верно (тот же приём, что и в
    # тесте честного отказа ниже).
    text = body["text"].lower()
    assert "стал" in text and "45" in text


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

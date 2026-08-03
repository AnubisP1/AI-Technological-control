from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_ask_assistant_endpoint_returns_real_material_match():
    response = client.post("/assistant/chat", json={"question": "Сталь 45"})
    assert response.status_code == 200
    body = response.json()
    assert body["generated_by"] == "template"
    assert "Сталь 45" in body["text"]


def test_ask_assistant_endpoint_handles_no_matches_without_hallucinating():
    response = client.post("/assistant/chat", json={"question": "зюзюкин Ы-9000 кварзоплетень"})
    assert response.status_code == 200
    body = response.json()
    assert "не найдено" in body["text"].lower()


def test_ask_assistant_endpoint_rejects_missing_question_field():
    response = client.post("/assistant/chat", json={})
    assert response.status_code == 422

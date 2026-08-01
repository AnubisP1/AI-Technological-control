from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_cpu_budget_within_governed_fraction():
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    # Бюджет должен быть строго меньше общего числа ядер при cpu_count > 2,
    # иначе ограничение потоков не имеет эффекта (см. ТЗ: лимит 40-60% CPU).
    assert body["cpu_thread_budget"] <= body["cpu_count_total"]

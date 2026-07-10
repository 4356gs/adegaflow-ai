from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_unversioned_health() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["service"] == "AdegaFlow AI API"
    assert isinstance(payload["qwen_configured"], bool)


def test_versioned_health() -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["version"] == "0.1.0"

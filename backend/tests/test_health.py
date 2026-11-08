from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_api_root_redirects_to_documentation() -> None:
    response = client.get("/", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "/docs"


def test_application_health_returns_ok() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

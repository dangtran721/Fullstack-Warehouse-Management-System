from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_frontend_origin_can_send_authenticated_requests() -> None:
    response = client.options(
        "/api/v1/auth/me",
        headers={
            "Origin": "http://localhost:5500",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5500"
    assert "authorization" in response.headers["access-control-allow-headers"].lower()

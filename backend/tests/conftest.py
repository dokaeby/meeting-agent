import pytest
from fastapi.testclient import TestClient

from meeting_agent.config import Settings
from meeting_agent.main import create_app


@pytest.fixture
def client(tmp_path):
    app = create_app(
        Settings(
            environment="test",
            database_url=f"sqlite:///{tmp_path}/test.db",
            storage_path=tmp_path / "files",
            provider_mode="test",
        )
    )
    with TestClient(app) as value:
        yield value


def signup(client, email="owner@example.com", name="관리자"):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Long-password-123!", "name": name},
    )
    assert response.status_code == 201, response.text
    token = response.json()["test_token"]
    assert client.post("/api/v1/auth/verify-email", json={"token": token}).status_code == 200
    result = client.post(
        "/api/v1/auth/login", json={"email": email, "password": "Long-password-123!"}
    )
    assert result.status_code == 200, result.text
    client.headers["X-CSRF-Token"] = result.json()["csrf_token"]
    return result.json()["user"]


@pytest.fixture
def owner(client):
    user = signup(client)
    response = client.post("/api/v1/organizations", json={"name": "테스트 회사"})
    assert response.status_code == 201, response.text
    return user, response.json()["id"]

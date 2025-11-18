from fastapi.testclient import TestClient
from services.users_service.main import app

client = TestClient(app)


def test_create_user():
    response = client.post(
        "/api/users",
        json={"username": "testuser", "password": "StrongPass123!"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "testuser"
    assert data["role"] == "regular"
    assert "id" in data


def test_list_users():
    response = client.get("/api/users")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert any(user["username"] == "testuser" for user in data)

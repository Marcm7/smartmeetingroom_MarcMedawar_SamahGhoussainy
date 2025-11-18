from fastapi.testclient import TestClient
from services.rooms_service.main import app

client = TestClient(app)


def test_create_room():
    response = client.post(
        "/api/rooms",
        json={
            "name": "Conference Room A",
            "location": "3rd floor - Building A",
            "capacity": 10
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Conference Room A"
    assert data["location"].startswith("3rd floor")
    assert data["capacity"] == 10
    assert "id" in data


def test_list_rooms():
    response = client.get("/api/rooms")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert any(room["name"] == "Conference Room A" for room in data)

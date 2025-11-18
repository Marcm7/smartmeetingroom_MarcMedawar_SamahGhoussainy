from fastapi.testclient import TestClient
from services.bookings_service.main import app

client = TestClient(app)


def test_create_booking():
    response = client.post(
        "/api/bookings",
        json={
            "room_id": 1,
            "username": "testuser",
            "start_time": "2025-01-01T10:00:00",
            "end_time": "2025-01-01T11:00:00",
            "purpose": "Test meeting",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["room_id"] == 1
    assert data["username"] == "testuser"
    assert data["status"] == "confirmed"

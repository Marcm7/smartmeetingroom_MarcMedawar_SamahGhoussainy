from fastapi.testclient import TestClient
from services.reviews_service.main import app

client = TestClient(app)


def test_create_review():
    response = client.post(
        "/api/rooms/1/reviews",
        json={
            "username": "testuser",
            "rating": 5,
            "comment": "Great room!",
            "booking_id": 1,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["room_id"] == 1
    assert data["username"] == "testuser"
    assert data["rating"] == 5

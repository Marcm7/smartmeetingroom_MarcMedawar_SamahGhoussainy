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
        headers={"Authorization": "Bearer testuser"},  # add this line
    )
    assert response.status_code == 201

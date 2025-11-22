from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from services.bookings_service.main import app

client = TestClient(app)


def run_load_test(iterations: int = 100):
    """
    Run a simple load test against the bookings API.

    Creates `iterations` bookings and then lists them once.
    """
    base_start = datetime.now()
    for i in range(iterations):
        payload = {
            "room_id": 1,
            "username": f"user{i}",
            "start_time": (base_start + timedelta(minutes=30 * i)).isoformat(),
            "end_time": (base_start + timedelta(minutes=30 * i + 25)).isoformat(),
            "purpose": "performance test",
        }
        response = client.post("/api/bookings", json=payload)
        response.raise_for_status()

    # One GET to retrieve all bookings
    response = client.get("/api/bookings")
    response.raise_for_status()


if __name__ == "__main__":
    run_load_test()

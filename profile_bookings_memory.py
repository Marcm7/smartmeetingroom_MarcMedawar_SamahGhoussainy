from memory_profiler import profile
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

from services.bookings_service.main import app

client = TestClient(app)


@profile
def memory_test():
    base_start = datetime.now()

    for i in range(50):
        payload = {
            "room_id": 1,
            "username": f"user{i}",
            "start_time": (base_start + timedelta(minutes=30 * i)).isoformat(),
            "end_time": (base_start + timedelta(minutes=30 * i + 25)).isoformat(),
            "purpose": "memory test",
        }
        client.post("/api/bookings", json=payload)

    client.get("/api/bookings")


if __name__ == "__main__":
    memory_test()

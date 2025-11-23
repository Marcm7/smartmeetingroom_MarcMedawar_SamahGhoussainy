"""
Rooms Service

This module defines the FastAPI service responsible for managing rooms
in the Smart Meeting Room system. It exposes endpoints to create new
rooms and list all existing rooms stored in the database.
"""

from fastapi import FastAPI, Depends, status
from sqlalchemy.orm import Session
import time
from typing import Any, Dict, Tuple, List
import socket

from .schemas import RoomCreate, RoomResponse
from . import models
from .database import engine, get_db


app = FastAPI(
    title="Rooms Service",
    description="Handles creation and retrieval of rooms in the system.",
)

@app.middleware("http")
async def add_instance_header(request, call_next):
    response = await call_next(request)
    response.headers["X-Instance"] = socket.gethostname()
    return response


CACHE: Dict[str, Tuple[float, Any]] = {}
CACHE_TTL = 30  # seconds


def cache_get(key: str):
    """
    Retrieve a cached value if not expired.
    Returns None if missing or expired.
    """
    item = CACHE.get(key)
    if not item:
        return None

    ts, data = item
    if time.time() - ts > CACHE_TTL:
        CACHE.pop(key, None)
        return None

    return data


def cache_set(key: str, data: Any):
    """Store value in cache with current timestamp."""
    CACHE[key] = (time.time(), data)


def cache_invalidate(prefix: str = ""):
    """
    Invalidate cached keys that start with a prefix.
    Useful when data changes.
    """
    keys = [k for k in CACHE if k.startswith(prefix)]
    for k in keys:
        CACHE.pop(k, None)


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "rooms"}


@app.post(
    "/api/rooms",
    response_model=RoomResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_room(room: RoomCreate, db: Session = Depends(get_db)) -> RoomResponse:
    """
    Create a new room in the system.

    This endpoint persists a new room record in the database using the
    attributes provided in the request body.

    Args:
        room: RoomCreate schema containing the room name, capacity, and
            any other configured attributes.
        db: Database session injected by FastAPI's dependency system.

    Returns:
        RoomResponse: Representation of the newly created room as stored
        in the database.
    """
    db_room = models.Room(**room.model_dump())
    db.add(db_room)
    db.commit()
    db.refresh(db_room)
    cache_invalidate("rooms:list")

    return RoomResponse.model_validate(db_room)


@app.get(
    "/api/rooms",
    response_model=list[RoomResponse],
)
def list_rooms(db: Session = Depends(get_db)) -> list[RoomResponse]:
    """
    Retrieve all rooms currently stored in the system.

    Args:
        db: Database session injected by FastAPI's dependency system.

    Returns:
        list[RoomResponse]: A list of all rooms available in the database.
    """
    cache_key = "rooms:list"
    cached = cache_get(cache_key)

    if cached is not None:
        print("⚡ rooms:list cache HIT")
        return cached

    print("🐢 rooms:list cache MISS")
    rooms = db.query(models.Room).all()
    rooms_data = [RoomResponse.model_validate(r) for r in rooms]

    cache_set(cache_key, rooms_data)
    return rooms_data

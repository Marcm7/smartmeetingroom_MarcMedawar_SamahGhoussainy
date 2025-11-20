"""
Rooms Service

This module defines the FastAPI service responsible for managing rooms
in the Smart Meeting Room system. It exposes endpoints to create new
rooms and list all existing rooms stored in the database.
"""

from fastapi import FastAPI, Depends, status
from sqlalchemy.orm import Session

from .schemas import RoomCreate, RoomResponse
from . import models
from .database import engine, get_db

# Create all database tables for the Room model if they do not exist yet.
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Rooms Service",
    description="Handles creation and retrieval of rooms in the system.",
)


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
    rooms = db.query(models.Room).all()
    return [RoomResponse.model_validate(r) for r in rooms]

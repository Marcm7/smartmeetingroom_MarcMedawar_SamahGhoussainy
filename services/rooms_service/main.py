"""
Rooms Service

This module defines the FastAPI service responsible for managing rooms
in the Smart Meeting Room system. It exposes endpoints to create new
rooms and list all existing rooms stored in the database.
"""

import logging
import os
import time
from logging.handlers import RotatingFileHandler

from fastapi import FastAPI, Depends, Request, status
from fastapi.exceptions import RequestValidationError
from sqlalchemy.orm import Session

from .schemas import RoomCreate, RoomResponse
from . import models
from .database import engine, get_db
from .exception_handlers import (
    validation_exception_handler,
    general_exception_handler,
)


# -------------------------------
# Audit logger setup (Part II – Auditing & Logging)
# -------------------------------

def get_audit_logger() -> logging.Logger:
    """
    Configure and return a logger that writes audit events for
    the Rooms service into <project_root>/logs/rooms_audit.log.
    """
    logger = logging.getLogger("rooms_audit")
    if logger.handlers:
        # Already configured (avoid adding handlers twice in reloads)
        return logger

    logger.setLevel(logging.INFO)

    # Project root: two levels up from this file
    # services/rooms_service/main.py -> services -> project_root
    base_dir = os.path.dirname(os.path.dirname(__file__))
    logs_dir = os.path.join(base_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)

    log_path = os.path.join(logs_dir, "rooms_audit.log")
    handler = RotatingFileHandler(log_path, maxBytes=1_000_000, backupCount=3)
    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger


audit_logger = get_audit_logger()


# -------------------------------
# FastAPI application
# -------------------------------

# Create all database tables for the Room model if they do not exist yet.
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Rooms Service",
    description="Handles creation and retrieval of rooms in the system.",
)

# Global exception handlers (Part 7 – Advanced Development Practices)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)


# Auditing middleware (Part II – Auditing & Logging)
@app.middleware("http")
async def audit_log_middleware(request: Request, call_next):
    """
    Middleware that logs each HTTP request with method, path, status,
    and processing time. User identity is logged if provided in the
    Authorization header as a Bearer token.
    """
    start = time.perf_counter()

    auth_header = request.headers.get("authorization", "")
    username = "anonymous"
    if auth_header.lower().startswith("bearer "):
        username = auth_header.split(" ", 1)[1].strip() or "anonymous"

    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000

    audit_logger.info(
        "method=%s path=%s user=%s status=%s duration_ms=%.2f",
        request.method,
        request.url.path,
        username,
        response.status_code,
        duration_ms,
    )

    return response


# -------------------------------
# API endpoints
# -------------------------------

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

    audit_logger.info(
        "CREATE room id=%s name=%s location=%s capacity=%s",
        db_room.id,
        db_room.name,
        getattr(db_room, "location", None),
        getattr(db_room, "capacity", None),
    )

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

    audit_logger.info(
        "LIST rooms count=%s",
        len(rooms),
    )

    return [RoomResponse.model_validate(r) for r in rooms]


@app.post(
    "/api/v1/rooms",
    response_model=RoomResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_room_v1(room: RoomCreate, db: Session = Depends(get_db)) -> RoomResponse:
    """
    API v1: Create a new room.
    This is a versioned wrapper around the legacy /api/rooms endpoint.
    """
    return create_room(room, db)


@app.get(
    "/api/v1/rooms",
    response_model=list[RoomResponse],
)
def list_rooms_v1(db: Session = Depends(get_db)) -> list[RoomResponse]:
    """
    API v1: List all rooms.
    This is a versioned wrapper around the legacy /api/rooms endpoint.
    """
    return list_rooms(db)

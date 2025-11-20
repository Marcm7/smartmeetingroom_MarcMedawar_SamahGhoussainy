"""
Bookings Service

This module defines the FastAPI service responsible for managing room
bookings in the Smart Meeting Room system. It exposes endpoints to
create, list, retrieve, update, and delete bookings.
"""

from datetime import datetime
from typing import List, Optional

import logging
import os
from logging.handlers import RotatingFileHandler

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.requests import Request
from pydantic import BaseModel

from . import models  # kept for consistency, even if not used directly
from .database import engine  # kept for consistency, even if not used directly


app = FastAPI(
    title="Bookings Service",
    version="0.1.0",
    description="Handles creation and management of room bookings.",
)


# -------------------------------
# Exception handlers (Task 7)
# -------------------------------

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handle validation errors in a consistent JSON format.
    """
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Invalid request payload.",
            "errors": exc.errors(),
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """
    Catch-all handler for unexpected server errors.
    """
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error."},
    )


# -------------------------------
# Audit logger setup (Task 2)
# -------------------------------

def get_audit_logger() -> logging.Logger:
    """
    Configure and return a logger that writes audit events for
    the Bookings service into logs/bookings_audit.log.
    """
    logger = logging.getLogger("bookings_audit")
    if logger.handlers:
        # Already configured (avoid adding handlers twice in reloads)
        return logger

    logger.setLevel(logging.INFO)

    # Project root: go three levels up from this file
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    logs_dir = os.path.join(base_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)

    log_path = os.path.join(logs_dir, "bookings_audit.log")
    handler = RotatingFileHandler(log_path, maxBytes=1_000_000, backupCount=3)
    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger


audit_logger = get_audit_logger()


# -------------------------------
# Pydantic schemas
# -------------------------------

class BookingCreate(BaseModel):
    """
    Schema for creating a new booking.

    Attributes:
        room_id: Identifier of the room being booked.
        username: Username of the person making the booking.
        start_time: Start datetime of the booking.
        end_time: End datetime of the booking (must be after start_time).
        purpose: Optional free-text description of the meeting purpose.
    """

    room_id: int
    username: str
    start_time: datetime
    end_time: datetime
    purpose: Optional[str] = None


class BookingUpdate(BaseModel):
    """
    Schema for updating an existing booking.

    Attributes:
        start_time: Optional new start datetime of the booking.
        end_time: Optional new end datetime of the booking.
        purpose: Optional new purpose text for the booking.
    """

    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    purpose: Optional[str] = None


class BookingResponse(BookingCreate):
    """
    Schema returned by the bookings API endpoints.

    Extends:
        BookingCreate: Includes all fields used for creation.

    Attributes:
        id: Unique identifier of the booking.
        status: Current status of the booking (e.g., "confirmed").
    """

    id: int
    status: str = "confirmed"


# In-memory storage for bookings; in a real deployment this would be backed by a database.
bookings: List[BookingResponse] = []
next_booking_id: int = 1


# -------------------------------
# Helper functions
# -------------------------------

def get_booking_or_404(booking_id: int) -> BookingResponse:
    """
    Retrieve a booking by its identifier or raise a 404 error.

    Args:
        booking_id: Unique identifier of the booking to retrieve.

    Returns:
        BookingResponse: The matching booking object.

    Raises:
        HTTPException: If no booking exists with the given identifier.
    """
    for b in bookings:
        if b.id == booking_id:
            return b
    raise HTTPException(status_code=404, detail="Booking not found")


# -------------------------------
# Base API endpoints
# -------------------------------

@app.get("/api/bookings", response_model=List[BookingResponse])
def list_bookings() -> List[BookingResponse]:
    """
    List all bookings currently stored in the system.

    Returns:
        List[BookingResponse]: A list of all bookings.
    """
    return bookings


@app.post("/api/bookings", response_model=BookingResponse, status_code=201)
def create_booking(payload: BookingCreate) -> BookingResponse:
    """
    Create a new booking.

    Validates that the end time is strictly after the start time, then
    stores the booking in the in-memory list.

    Args:
        payload: BookingCreate object containing room, user, time range,
            and optional purpose.

    Returns:
        BookingResponse: The created booking including its generated
        identifier and status.

    Raises:
        HTTPException: If the time interval is invalid (end before or equal to start).
    """
    global next_booking_id

    if payload.end_time <= payload.start_time:
        raise HTTPException(status_code=400, detail="end_time must be after start_time")

    booking = BookingResponse(
        id=next_booking_id,
        room_id=payload.room_id,
        username=payload.username,
        start_time=payload.start_time,
        end_time=payload.end_time,
        purpose=payload.purpose,
        status="confirmed",
    )
    next_booking_id += 1
    bookings.append(booking)

    # Audit logging (Task 2)
    audit_logger.info(
        "CREATE booking id=%s room_id=%s user=%s start=%s end=%s",
        booking.id,
        booking.room_id,
        booking.username,
        booking.start_time.isoformat(),
        booking.end_time.isoformat(),
    )

    return booking


@app.get("/api/bookings/{booking_id}", response_model=BookingResponse)
def get_booking(booking_id: int) -> BookingResponse:
    """
    Retrieve a single booking by its identifier.

    Args:
        booking_id: Identifier of the booking to retrieve.

    Returns:
        BookingResponse: The matching booking.

    Raises:
        HTTPException: If the booking does not exist.
    """
    return get_booking_or_404(booking_id)


@app.put("/api/bookings/{booking_id}", response_model=BookingResponse)
def update_booking(booking_id: int, payload: BookingUpdate) -> BookingResponse:
    """
    Update an existing booking.

    Allows changing the start time, end time, and/or purpose while
    ensuring that the resulting time interval remains valid.

    Args:
        booking_id: Identifier of the booking to update.
        payload: BookingUpdate object with new values for the booking.

    Returns:
        BookingResponse: The updated booking.

    Raises:
        HTTPException: If the updated time interval is invalid or the booking does not exist.
    """
    booking = get_booking_or_404(booking_id)

    if payload.start_time is not None:
        booking.start_time = payload.start_time

    if payload.end_time is not None:
        # If both start and end are provided in the payload.
        if payload.start_time is not None and payload.end_time <= payload.start_time:
            raise HTTPException(status_code=400, detail="end_time must be after start_time")
        # If only end_time is provided, compare with existing start_time.
        if payload.start_time is None and payload.end_time <= booking.start_time:
            raise HTTPException(status_code=400, detail="end_time must be after start_time")
        booking.end_time = payload.end_time

    if payload.purpose is not None:
        booking.purpose = payload.purpose

    # Audit logging (Task 2)
    audit_logger.info(
        "UPDATE booking id=%s room_id=%s user=%s start=%s end=%s purpose=%s",
        booking.id,
        booking.room_id,
        booking.username,
        booking.start_time.isoformat(),
        booking.end_time.isoformat(),
        booking.purpose,
    )

    return booking


@app.delete("/api/bookings/{booking_id}")
def delete_booking(booking_id: int) -> dict:
    """
    Cancel (delete) an existing booking.

    Args:
        booking_id: Identifier of the booking to delete.

    Returns:
        dict: A confirmation message containing the identifier of the deleted booking.

    Raises:
        HTTPException: If the booking does not exist.
    """
    booking = get_booking_or_404(booking_id)
    bookings.remove(booking)

    # Audit logging (Task 2)
    audit_logger.info(
        "DELETE booking id=%s room_id=%s user=%s",
        booking.id,
        booking.room_id,
        booking.username,
    )

    return {"message": "Booking cancelled successfully", "booking_id": booking_id}


# ------------------------------
# API v1 versioned endpoints (Task 7)
# ------------------------------

@app.get("/api/v1/bookings", response_model=List[BookingResponse])
def list_bookings_v1() -> List[BookingResponse]:
    """API v1: List all bookings (same logic as /api/bookings)."""
    return list_bookings()


@app.post("/api/v1/bookings", response_model=BookingResponse, status_code=201)
def create_booking_v1(payload: BookingCreate) -> BookingResponse:
    """API v1: Create a new booking (same logic as /api/bookings)."""
    return create_booking(payload)


@app.get("/api/v1/bookings/{booking_id}", response_model=BookingResponse)
def get_booking_v1(booking_id: int) -> BookingResponse:
    """API v1: Get a single booking by ID."""
    return get_booking(booking_id)


@app.put("/api/v1/bookings/{booking_id}", response_model=BookingResponse)
def update_booking_v1(booking_id: int, payload: BookingUpdate) -> BookingResponse:
    """API v1: Update an existing booking."""
    return update_booking(booking_id, payload)


@app.delete("/api/v1/bookings/{booking_id}")
def delete_booking_v1(booking_id: int) -> dict:
    """API v1: Delete (cancel) a booking."""
    return delete_booking(booking_id)

"""
Bookings Service

This module defines the FastAPI service responsible for managing room
bookings in the Smart Meeting Room system. It exposes endpoints to
create, list, retrieve, update, and delete bookings.
"""

from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from . import models
from .database import engine


app = FastAPI(
    title="Bookings Service",
    version="0.1.0",
    description="Handles creation and management of room bookings.",
)


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
    return {"message": "Booking cancelled successfully", "booking_id": booking_id}

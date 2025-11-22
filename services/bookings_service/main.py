from datetime import datetime
from typing import List, Optional

from . import models
from .database import engine

import os
import json
import pika
from fastapi.encoders import jsonable_encoder

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(
    title="Bookings Service",
    version="0.1.0"
)

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")

def publish_booking_created(booking_obj):
    try:
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=RABBITMQ_HOST)
        )
        channel = connection.channel()
        channel.queue_declare(queue="booking_created", durable=True)

        payload = jsonable_encoder(booking_obj)

        body = json.dumps(payload)
        channel.basic_publish(
            exchange="",
            routing_key="booking_created",
            body=body,
            properties=pika.BasicProperties(delivery_mode=2),
        )
        connection.close()
        print("✅ Published booking_created event:", payload)

    except Exception as e:
        print("❌ Failed to publish event:", str(e))


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "bookings"}


class BookingCreate(BaseModel):
    room_id: int
    username: str
    start_time: datetime
    end_time: datetime
    purpose: Optional[str] = None


class BookingUpdate(BaseModel):
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    purpose: Optional[str] = None


class BookingResponse(BookingCreate):
    id: int
    status: str = "confirmed"


bookings: List[BookingResponse] = []
next_booking_id: int = 1


def get_booking_or_404(booking_id: int) -> BookingResponse:
    for b in bookings:
        if b.id == booking_id:
            return b
    raise HTTPException(status_code=404, detail="Booking not found")

@app.get("/api/bookings", response_model=List[BookingResponse])
def list_bookings() -> List[BookingResponse]:
    """List all bookings."""
    return bookings


@app.post("/api/bookings", response_model=BookingResponse, status_code=201)
def create_booking(payload: BookingCreate) -> BookingResponse:
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

    publish_booking_created(booking)

    return booking





@app.get("/api/bookings/{booking_id}", response_model=BookingResponse)
def get_booking(booking_id: int) -> BookingResponse:
    """Get a single booking by ID."""
    return get_booking_or_404(booking_id)


@app.put("/api/bookings/{booking_id}", response_model=BookingResponse)
def update_booking(booking_id: int, payload: BookingUpdate) -> BookingResponse:
    """Update an existing booking."""
    booking = get_booking_or_404(booking_id)

    if payload.start_time is not None:
        booking.start_time = payload.start_time
    if payload.end_time is not None:
        if payload.start_time is not None and payload.end_time <= payload.start_time:
            raise HTTPException(status_code=400, detail="end_time must be after start_time")
        if payload.start_time is None and payload.end_time <= booking.start_time:
            raise HTTPException(status_code=400, detail="end_time must be after start_time")
        booking.end_time = payload.end_time
    if payload.purpose is not None:
        booking.purpose = payload.purpose

    return booking


@app.delete("/api/bookings/{booking_id}")
def delete_booking(booking_id: int) -> dict:
    """Cancel (delete) a booking."""
    booking = get_booking_or_404(booking_id)
    bookings.remove(booking)
    return {"message": "Booking cancelled successfully", "booking_id": booking_id}

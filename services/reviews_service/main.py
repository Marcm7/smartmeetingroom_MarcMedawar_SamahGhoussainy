from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from . import models
from .database import engine
import os
import json
import pika
import threading



app = FastAPI(
    title="Reviews Service",
    version="0.1.0",
    description="Handles room reviews for the Smart Meeting Room system."
)

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "reviews"}


class ReviewCreate(BaseModel):
    username: str
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None
    booking_id: int


class ReviewUpdate(BaseModel):
    rating: Optional[int] = Field(None, ge=1, le=5)
    comment: Optional[str] = None


class ReviewResponse(BaseModel):
    review_id: int
    room_id: int
    username: str
    rating: int
    comment: Optional[str]
    booking_id: int
    created_at: datetime

reviews: List[ReviewResponse] = []
_next_review_id: int = 1


def get_review_or_404(review_id: int) -> ReviewResponse:
    for r in reviews:
        if r.review_id == review_id:
            return r
    raise HTTPException(status_code=404, detail="Review not found")

def start_booking_consumer():
    try:
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=RABBITMQ_HOST)
        )
        channel = connection.channel()
        channel.queue_declare(queue="booking_created", durable=True)

        def callback(ch, method, properties, body):
            data = json.loads(body)
            print("📩 Reviews-service received booking_created event:", data)
            ch.basic_ack(delivery_tag=method.delivery_tag)

        channel.basic_qos(prefetch_count=1)
        channel.basic_consume(queue="booking_created", on_message_callback=callback)

        print("🚀 Reviews-service waiting for booking_created events...")
        channel.start_consuming()

    except Exception as e:
        print("❌ Reviews-service consumer error:", repr(e))



@app.on_event("startup")
def startup_event():
    thread = threading.Thread(target=start_booking_consumer, daemon=True)
    thread.start()

@app.post("/api/rooms/{room_id}/reviews", response_model=ReviewResponse, status_code=201)
def create_review(room_id: int, payload: ReviewCreate) -> ReviewResponse:
    global _next_review_id

    review = ReviewResponse(
        review_id=_next_review_id,
        room_id=room_id,
        username=payload.username,
        rating=payload.rating,
        comment=payload.comment,
        booking_id=payload.booking_id,
        created_at=datetime.utcnow(),
    )
    reviews.append(review)
    _next_review_id += 1
    return review


@app.get("/api/rooms/{room_id}/reviews", response_model=List[ReviewResponse])
def list_room_reviews(room_id: int) -> List[ReviewResponse]:
    return [r for r in reviews if r.room_id == room_id]


@app.put("/api/reviews/{review_id}", response_model=ReviewResponse)
def update_review(review_id: int, payload: ReviewUpdate) -> ReviewResponse:
    review = get_review_or_404(review_id)

    if payload.rating is not None:
        review.rating = payload.rating
    if payload.comment is not None:
        review.comment = payload.comment

    return review


@app.delete("/api/reviews/{review_id}")
def delete_review(review_id: int) -> dict:
    review = get_review_or_404(review_id)
    reviews.remove(review)
    return {"message": "Review deleted successfully", "review_id": review_id}



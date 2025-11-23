"""
Reviews Service

This module defines the FastAPI service responsible for handling room reviews
in the Smart Meeting Room system. It exposes endpoints to create, list,
update, and delete reviews associated with room bookings, with input
validation, basic sanitization, and simple token-based authentication.

Authentication & Authorization (Part 12)
---------------------------------------
- We assume there is a separate Users Service that issues bearer tokens
  at POST /api/users/login.
- In this project, the access token is simply the username.
- Only authenticated users (i.e. requests with a valid Authorization header)
  can create, update, or delete reviews.
- Additionally:
    * When creating a review, the username in the payload must match
      the authenticated username.
    * When updating or deleting a review, only the user who created the
      review is allowed to modify/delete it.
"""

from datetime import datetime
from typing import List, Optional

import os, json, pika, threading
from pydantic import BaseModel, Field, field_validator
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from . import models
from .database import engine

app = FastAPI(
    title="Reviews Service",
    version="0.1.0",
    description="Handles room reviews for the Smart Meeting Room system.",
)

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")

bearer_scheme = HTTPBearer(auto_error=True)

def get_current_username(
    creds: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> str:
    """
    Extract the username from the Authorization header.

    Expected header:
        Authorization: Bearer <username>

    Returns:
        str: authenticated username
    """
    token = creds.credentials.strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid bearer token.",
        )
    return token


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "reviews"}

class ReviewCreate(BaseModel):
    """
    Schema for creating a new review.

    Attributes:
        username: Username of the reviewer (alphanumeric + underscore, 3–30 chars).
        rating: Integer rating between 1 and 5 inclusive.
        comment: Optional free-text comment about the room/booking (max 500 chars).
        booking_id: Identifier of the booking this review is linked to (must be positive).
    """

    username: str = Field(
        ...,
        min_length=3,
        max_length=30,
        pattern=r"^[A-Za-z0-9_]+$",
    )
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = Field(None, max_length=500)
    booking_id: int = Field(..., gt=0)

    @field_validator("comment")
    @classmethod
    def sanitize_comment(cls, value: Optional[str]) -> Optional[str]:
        """
        Strip leading/trailing whitespace and reject obviously dangerous patterns.

        This is not a replacement for parameterized queries, but adds a layer
        of defense against naive SQL injection attempts in free-text fields.
        """
        if value is None:
            return value

        cleaned = value.strip()
        lowered = cleaned.lower()

        dangerous_tokens = [
            "--",
            ";--",
            ";",
            "/*",
            "*/",
            "@@",
            " xp_",
            " drop ",
            " delete ",
            " insert ",
            " update ",
            " alter ",
            " create ",
        ]
        for token in dangerous_tokens:
            if token in lowered:
                raise ValueError("Comment contains disallowed characters or patterns.")

        return cleaned


class ReviewUpdate(BaseModel):
    """
    Schema for updating an existing review.

    Attributes:
        rating: Optional new rating between 1 and 5 inclusive.
        comment: Optional new comment text (max 500 chars) to replace the old one.
    """

    rating: Optional[int] = Field(None, ge=1, le=5)
    comment: Optional[str] = Field(None, max_length=500)

    @field_validator("comment")
    @classmethod
    def sanitize_comment(cls, value: Optional[str]) -> Optional[str]:
        """
        Apply the same sanitization rules as in ReviewCreate for updated comments.
        """
        if value is None:
            return value

        cleaned = value.strip()
        lowered = cleaned.lower()

        dangerous_tokens = [
            "--",
            ";--",
            ";",
            "/*",
            "*/",
            "@@",
            " xp_",
            " drop ",
            " delete ",
            " insert ",
            " update ",
            " alter ",
            " create ",
        ]
        for token in dangerous_tokens:
            if token in lowered:
                raise ValueError("Comment contains disallowed characters or patterns.")

        return cleaned


class ReviewResponse(BaseModel):
    """
    Schema returned by the reviews API endpoints.

    Attributes:
        review_id: Unique identifier of the review.
        room_id: Identifier of the room being reviewed.
        username: Username of the reviewer.
        rating: Rating given to the room.
        comment: Optional textual comment describing the experience.
        booking_id: Identifier of the associated booking.
        created_at: UTC timestamp when the review was created.
    """

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
    """
    Retrieve a review by its identifier or raise a 404 error.

    Args:
        review_id: Unique identifier of the review to retrieve.

    Returns:
        ReviewResponse: The matching review object.

    Raises:
        HTTPException: If no review exists with the given identifier.
    """
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
async def create_review(
    room_id: int,
    payload: ReviewCreate,
    current_username: str = Depends(get_current_username),
) -> ReviewResponse:
    """
    Create a new review for a given room.

    Authentication:
        - Requires a valid bearer token.
        - The token (username) must match payload.username.

    Args:
        room_id: Identifier of the room being reviewed.
        payload: ReviewCreate object containing username, rating, comment,
            and booking identifier.
        current_username: Injected from the bearer token by get_current_username.

    Returns:
        ReviewResponse: The created review including its generated identifier
        and creation timestamp.

    Raises:
        HTTPException: 403 if the payload username does not match the
        authenticated username.
    """
    global _next_review_id

    if payload.username != current_username:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only create reviews as yourself.",
        )

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
    """
    List all reviews for a specific room.

    This endpoint is left open (no authentication) so that anyone can read
    reviews, but only authenticated users can create, update, or delete them.

    Args:
        room_id: Identifier of the room whose reviews should be returned.

    Returns:
        List[ReviewResponse]: All reviews that belong to the specified room.
    """
    return [r for r in reviews if r.room_id == room_id]


@app.put("/api/reviews/{review_id}", response_model=ReviewResponse)
async def update_review(
    review_id: int,
    payload: ReviewUpdate,
    current_username: str = Depends(get_current_username),
) -> ReviewResponse:
    """
    Update the rating and/or comment of an existing review.

    Authentication:
        - Requires a valid bearer token.
        - Only the author of the review is allowed to update it.

    Args:
        review_id: Identifier of the review that should be updated.
        payload: ReviewUpdate object containing the new rating and/or comment.
        current_username: Injected from the bearer token.

    Returns:
        ReviewResponse: The updated review object.

    Raises:
        HTTPException:
            * 404 if the review does not exist.
            * 403 if the current user is not the author.
    """
    review = get_review_or_404(review_id)

    if review.username != current_username:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own reviews.",
        )

    if payload.rating is not None:
        review.rating = payload.rating
    if payload.comment is not None:
        review.comment = payload.comment

    return review


@app.delete("/api/reviews/{review_id}")
async def delete_review(
    review_id: int,
    current_username: str = Depends(get_current_username),
) -> dict:
    """
    Delete an existing review.

    Authentication:
        - Requires a valid bearer token.
        - Only the author of the review is allowed to delete it.

    Args:
        review_id: Identifier of the review to delete.
        current_username: Injected from the bearer token.

    Returns:
        dict: A confirmation message including the identifier of the deleted review.

    Raises:
        HTTPException:
            * 404 if the review does not exist.
            * 403 if the current user is not the author.
    """
    review = get_review_or_404(review_id)

    if review.username != current_username:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own reviews.",
        )

    reviews.remove(review)
    return {"message": "Review deleted successfully", "review_id": review_id}

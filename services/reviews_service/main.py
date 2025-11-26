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

import logging
import os
import time
from logging.handlers import RotatingFileHandler

from fastapi import FastAPI, HTTPException, Depends, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, Field, field_validator

from .exception_handlers import (
    validation_exception_handler,
    general_exception_handler,
)

# -------------------------------
# Audit logger setup (Part II - Advanced Security: Auditing & Logging)
# -------------------------------

def get_audit_logger() -> logging.Logger:
    """
    Configure and return a logger that writes audit events for
    the Reviews service into <project_root>/logs/reviews_audit.log.
    """
    logger = logging.getLogger("reviews_audit")
    if logger.handlers:
        # Already configured (avoid adding handlers twice in reloads)
        return logger

    logger.setLevel(logging.INFO)

    # Project root: two levels up from this file
    # services/reviews_service/main.py -> services -> project_root
    base_dir = os.path.dirname(os.path.dirname(__file__))
    logs_dir = os.path.join(base_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)

    log_path = os.path.join(logs_dir, "reviews_audit.log")
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

app = FastAPI(
    title="Reviews Service",
    version="0.1.0",
    description="Handles room reviews for the Smart Meeting Room system.",
)

# Global exception handlers (Part 7 – Advanced Development Practices)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)


# Auditing middleware (Part II – Auditing & Logging)
@app.middleware("http")
async def audit_log_middleware(request: Request, call_next):
    """
    Middleware that logs each HTTP request with method, path, user,
    status code, and processing time.
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
# Authentication helper
# -------------------------------

# In this project, the Users Service issues tokens where the token value is
# simply the username. We treat that as the authenticated identity.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/users/login")


async def get_current_username(token: str = Depends(oauth2_scheme)) -> str:
    """
    Extract the current username from the bearer token.

    For this assignment, the token itself is assumed to be the username;
    in a real-world application it would be a signed JWT that we would
    decode and validate.
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token


# -------------------------------
# Pydantic schemas
# -------------------------------

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
        # Very simple blacklist of suspicious SQL tokens/sequences
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


# -------------------------------
# In-memory storage
# -------------------------------

# In a real deployment this would be backed by a database.
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


# -------------------------------
# API endpoints
# -------------------------------

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

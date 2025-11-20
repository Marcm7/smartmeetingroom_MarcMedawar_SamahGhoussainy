"""
Users Service

This module defines the FastAPI application entrypoint for the users
service in the Smart Meeting Room system. It is responsible for
initializing the database tables and including the API router that
exposes user-related endpoints (registration, login, profile, etc.).
"""

from fastapi import FastAPI

from . import models
from .database import engine
from .routes import router as users_router

# Create all database tables for the User model if they do not exist yet.
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Users Service",
    description="Handles user-related operations for the Smart Meeting Room system.",
)

# Mount the users router so that all user endpoints are exposed under this app.
app.include_router(users_router)

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

app = FastAPI(title="Users Service")

app.include_router(users_router)

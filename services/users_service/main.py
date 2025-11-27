"""
Users Service

This module defines the FastAPI application entrypoint for the users
service in the Smart Meeting Room system. It is responsible for
initializing the database tables and including the API router that
exposes user-related endpoints (registration, login, profile, etc.).
"""

import logging
import os
import time
from logging.handlers import RotatingFileHandler

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError

from . import models
from .database import engine
from .routes import router as users_router
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
    the Users service into <project_root>/logs/users_audit.log.
    """
    logger = logging.getLogger("users_audit")
    if logger.handlers:
        # Already configured (avoid adding handlers twice in reloads)
        return logger

    logger.setLevel(logging.INFO)

    # Project root: two levels up from this file
    # services/users_service/main.py -> services -> project_root
    base_dir = os.path.dirname(os.path.dirname(__file__))
    logs_dir = os.path.join(base_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)

    log_path = os.path.join(logs_dir, "users_audit.log")
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

# Create all database tables for the User model if they do not exist yet.
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Users Service",
    description="Handles user-related operations for the Smart Meeting Room system.",
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
# Routers
# -------------------------------

# Expose legacy (unversioned) API: /api/users/...
app.include_router(users_router, prefix="/api")

# Expose versioned API: /api/v1/users/...
app.include_router(users_router, prefix="/api/v1")


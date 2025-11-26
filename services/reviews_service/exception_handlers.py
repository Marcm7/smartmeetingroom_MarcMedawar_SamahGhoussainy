from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from starlette.status import (
    HTTP_422_UNPROCESSABLE_ENTITY,
    HTTP_500_INTERNAL_SERVER_ERROR,
)


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handle FastAPI request validation errors (e.g. invalid/missing fields in body, params).
    """
    return JSONResponse(
        status_code=HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Invalid request payload.",
            # Use string form to avoid non-serializable objects inside exc.errors()
            "errors": [str(exc)],
        },
    )


async def pydantic_validation_exception_handler(request: Request, exc: ValidationError):
    """
    Handle Pydantic model validation errors (e.g. field_validator raising ValueError).
    """
    return JSONResponse(
        status_code=HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Invalid request payload.",
            # Same here: make sure content is JSON serializable
            "errors": [str(exc)],
        },
    )


async def general_exception_handler(request: Request, exc: Exception):
    """
    Catch-all handler for unexpected server errors.
    """
    return JSONResponse(
        status_code=HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "An unexpected error occurred. Please try again later."
        },
    )

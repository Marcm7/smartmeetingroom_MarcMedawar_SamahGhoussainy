from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR, HTTP_422_UNPROCESSABLE_ENTITY


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handle FastAPI request validation errors (e.g. invalid/missing fields in body, params)
    in a standardized JSON format used across all services.
    """
    return JSONResponse(
        status_code=HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error": "ValidationError",
            "details": exc.errors(),
            "message": "Your request contains invalid or missing fields.",
        },
    )
async def pydantic_validation_exception_handler(request: Request, exc: ValidationError):
    """
    Handle Pydantic model validation errors in the same standardized format.
    """
    return JSONResponse(
        status_code=HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error": "ValidationError",
            "details": exc.errors(),
            "message": "Your request contains invalid or missing fields.",
        },
    )
async def general_exception_handler(request: Request, exc: Exception):
    """
    Catch-all handler for unexpected server errors.
    """
    return JSONResponse(
        status_code=HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": "ServerError",
            "message": "An unexpected error occurred. Please try again later.",
        },
    )

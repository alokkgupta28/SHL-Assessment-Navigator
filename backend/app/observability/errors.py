"""Application error taxonomy.

Every error the API can produce derives from :class:`AppError`. The HTTP
layer maps it to a stable JSON envelope so the frontend can branch on
``error.code`` rather than scraping prose. Stack traces stay on the
server; clients only see the code, a safe message, and the request id.
"""
from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .context import get_request_id
from .logging import get_logger

log = get_logger(__name__)


class AppError(Exception):
    """Base class for all expected application errors."""

    code: str = "internal_error"
    http_status: int = 500
    message: str = "Internal server error."

    def __init__(self, message: str | None = None, **details: Any) -> None:
        super().__init__(message or self.message)
        self.message = message or self.message
        self.details = details


class ValidationError(AppError):
    code = "validation_error"
    http_status = 422
    message = "Request failed validation."


class SafetyBlocked(AppError):
    code = "safety_blocked"
    http_status = 200  # surfaced inside the normal ChatResponse envelope
    message = "Request blocked by safety policy."


class CatalogUnavailable(AppError):
    code = "catalog_unavailable"
    http_status = 503
    message = "Assessment catalog is not loaded."


class RetrievalError(AppError):
    code = "retrieval_error"
    http_status = 500
    message = "Retrieval pipeline failed."


class LLMUnavailable(AppError):
    code = "llm_unavailable"
    http_status = 503
    message = "Language model is unavailable; falling back to deterministic logic."


class RateLimited(AppError):
    code = "rate_limited"
    http_status = 429
    message = "Too many requests. Please slow down."


class NotReady(AppError):
    code = "not_ready"
    http_status = 503
    message = "Service is still warming up."


def _envelope(code: str, message: str, status_code: int, **extra: Any) -> JSONResponse:
    body = {
        "error": {
            "code": code,
            "message": message,
            "request_id": get_request_id(),
        }
    }
    if extra:
        body["error"]["details"] = extra
    return JSONResponse(status_code=status_code, content=body)


def install_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError) -> JSONResponse:
        log.warning("app_error", extra={"code": exc.code, **exc.details})
        return _envelope(exc.code, exc.message, exc.http_status, **exc.details)

    @app.exception_handler(RequestValidationError)
    async def _pydantic(_: Request, exc: RequestValidationError) -> JSONResponse:
        log.info("validation_error", extra={"errors": exc.errors()[:5]})
        return _envelope(
            "validation_error",
            "Request body failed validation.",
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            issues=exc.errors()[:5],
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        return _envelope(
            f"http_{exc.status_code}",
            str(exc.detail) if exc.detail else "HTTP error.",
            exc.status_code,
        )

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception) -> JSONResponse:
        log.exception("unhandled_exception", extra={"type": type(exc).__name__})
        return _envelope(
            "internal_error",
            "An unexpected error occurred.",
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

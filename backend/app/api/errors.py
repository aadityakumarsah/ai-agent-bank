"""
Central HTTP exception handlers.

Rules:
* Client (4xx) errors get a clean, actionable ``detail``.
* Expected domain errors map to friendly messages (no stack traces).
* Anything unexpected is logged server-side with a traceback and re-shaped into
  a generic 500 message so users never see internal details.
"""

import traceback

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import get_logger
from app.services.errors import AIBankError

logger = get_logger("app.errors")


def _log_unexpected(request: Request, exc: Exception) -> None:
    logger.error(
        "unhandled error on %s %s: %s -> %s",
        request.method,
        request.url.path,
        type(exc).__name__,
        exc,
        exc_info=(type(exc), exc, exc.__traceback__),
    )
    try:
        traceback.print_exc()
    except Exception:  # noqa: BLE001
        pass


def install_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AIBankError)
    async def aibank_error_handler(request: Request, exc: AIBankError):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail, "code": exc.code, "error": exc.code},
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        logger.warning("validation error on %s %s: %s", request.method, request.url.path, exc)
        return JSONResponse(
            status_code=422,
            content={
                "detail": "One of the supplied values is invalid. Check the fields and try again.",
                "errors": exc.errors(),
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        _log_unexpected(request, exc)
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Something went wrong on our side. Please try again.",
                "code": "internal_error",
            },
        )
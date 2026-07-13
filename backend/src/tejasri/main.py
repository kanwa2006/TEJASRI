"""Application composition root.

Builds the FastAPI app, configures structured logging, installs the
trace-id middleware, and maps application errors to HTTP responses.
"""

import uuid
from collections.abc import Awaitable, Callable

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from tejasri import __version__
from tejasri.api.v1 import health
from tejasri.core.config import get_settings
from tejasri.core.errors import (
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    ExternalServiceError,
    NotFoundError,
    TejasriError,
    ValidationError,
)
from tejasri.core.logging import configure_logging, get_logger

_ERROR_STATUS: dict[type[TejasriError], int] = {
    NotFoundError: 404,
    ConflictError: 409,
    AuthenticationError: 401,
    AuthorizationError: 403,
    ValidationError: 422,
    ExternalServiceError: 502,
}

DISCLAIMER = (
    "TEJASRI is an assistive tool, not a medical device. It does not diagnose, "
    "prescribe, or replace clinical judgment. All data is synthetic."
)


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.tejasri_log_level)
    log = get_logger("tejasri")

    app = FastAPI(
        title="TEJASRI",
        summary="Healthcare Memory Platform — healthcare should never forget.",
        description=DISCLAIMER,
        version=__version__,
        docs_url=None if settings.is_production else "/docs",
        redoc_url=None,
    )

    @app.middleware("http")
    async def trace_requests(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        trace_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(trace_id=trace_id)
        response = await call_next(request)
        response.headers["x-request-id"] = trace_id
        log.info(
            "request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
        )
        return response

    @app.exception_handler(TejasriError)
    async def handle_tejasri_error(request: Request, exc: TejasriError) -> JSONResponse:
        status = _ERROR_STATUS.get(type(exc), 500)
        if status >= 500:
            log.error("application_error", error=type(exc).__name__, detail=exc.message)
        return JSONResponse(
            status_code=status,
            content={"error": type(exc).__name__, "detail": exc.message},
        )

    app.include_router(health.router, prefix="/api/v1")

    log.info("app_created", version=__version__, environment=settings.tejasri_env.value)
    return app


app = create_app()

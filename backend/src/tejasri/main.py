"""Application composition root.

Builds the FastAPI app, configures structured logging, installs the
trace-id middleware, and maps application errors to HTTP responses.
"""

import time
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse, PlainTextResponse

from tejasri import __version__
from tejasri.api.v1 import agent, auth, care_plans, health, notes, patients, tasks, timeline
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
from tejasri.core.metrics import metrics
from tejasri.core.ratelimit import TokenBucketLimiter
from tejasri.infrastructure.db import Database

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

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        # The pool connects lazily on first use, so the API can boot (and
        # report degraded readiness) even while the database is down.
        app.state.database = Database(settings.database_url)
        yield
        await app.state.database.close()

    app = FastAPI(
        lifespan=lifespan,
        title="TEJASRI",
        summary="Healthcare Memory Platform — healthcare should never forget.",
        description=DISCLAIMER,
        version=__version__,
        docs_url=None if settings.is_production else "/docs",
        redoc_url=None,
    )

    # Auth endpoints get a strict bucket (credential stuffing); the rest of
    # the API a generous one. In-memory: per-process, reset on restart —
    # a Redis-backed limiter slots in behind the same interface for scale.
    auth_limiter = TokenBucketLimiter(capacity=10, refill_per_minute=10)
    api_limiter = TokenBucketLimiter(capacity=120, refill_per_minute=240)
    app.state.rate_limiters = (auth_limiter, api_limiter)

    @app.middleware("http")
    async def trace_requests(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        trace_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(trace_id=trace_id)

        client_key = request.client.host if request.client else "unknown"
        limiter = auth_limiter if request.url.path.startswith("/api/v1/auth") else api_limiter
        if not limiter.allow(client_key):
            return JSONResponse(
                status_code=429,
                content={"error": "RateLimited", "detail": "too many requests"},
                headers={"retry-after": "30", "x-request-id": trace_id},
            )

        started = time.perf_counter()
        response = await call_next(request)
        elapsed = time.perf_counter() - started

        response.headers["x-request-id"] = trace_id
        response.headers["x-content-type-options"] = "nosniff"
        response.headers["x-frame-options"] = "DENY"
        response.headers["referrer-policy"] = "no-referrer"
        if settings.is_production:
            response.headers["strict-transport-security"] = "max-age=63072000; includeSubDomains"

        # Route templates (not raw paths) keep metrics cardinality bounded.
        route = request.scope.get("route")
        path_label = getattr(route, "path", request.url.path)
        metrics.observe_request(request.method, path_label, response.status_code, elapsed)
        log.info(
            "request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=round(elapsed * 1000, 2),
        )
        return response

    @app.get("/metrics", include_in_schema=False)
    async def metrics_endpoint() -> PlainTextResponse:
        return PlainTextResponse(metrics.render(), media_type="text/plain; version=0.0.4")

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
    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(patients.router, prefix="/api/v1")
    app.include_router(notes.router, prefix="/api/v1")
    app.include_router(care_plans.router, prefix="/api/v1")
    app.include_router(tasks.router, prefix="/api/v1")
    app.include_router(agent.router, prefix="/api/v1")
    app.include_router(timeline.router, prefix="/api/v1")

    log.info("app_created", version=__version__, environment=settings.tejasri_env.value)
    return app


app = create_app()

"""Health and readiness endpoints.

`/health` is a pure liveness probe — no dependencies, always answerable.
`/health/ready` additionally verifies the database is reachable.
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from tejasri import __version__
from tejasri.api.deps import get_database
from tejasri.core.config import get_settings
from tejasri.infrastructure.db import Database

router = APIRouter(prefix="/health", tags=["health"])


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str


class ReadinessResponse(BaseModel):
    status: str
    database: str


@router.get("", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Liveness probe: the process is up and serving requests."""
    settings = get_settings()
    return HealthResponse(
        status="ok",
        version=__version__,
        environment=settings.tejasri_env.value,
    )


@router.get("/ready", response_model=ReadinessResponse)
async def ready(db: Annotated[Database, Depends(get_database)]) -> ReadinessResponse:
    """Readiness probe: dependencies (the memory layer) are reachable."""
    try:
        database_status = "ok" if await db.ping() else "unreachable"
    except Exception:  # noqa: BLE001 — readiness must report, not crash
        database_status = "unreachable"
    status = "ok" if database_status == "ok" else "degraded"
    return ReadinessResponse(status=status, database=database_status)

"""Health and readiness endpoints.

`/health` is a pure liveness probe. `/health/ready` will additionally
verify the database connection once the persistence layer lands (Phase 2).
"""

from fastapi import APIRouter
from pydantic import BaseModel

from tejasri import __version__
from tejasri.core.config import get_settings

router = APIRouter(prefix="/health", tags=["health"])


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str


@router.get("", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Liveness probe: the process is up and serving requests."""
    settings = get_settings()
    return HealthResponse(
        status="ok",
        version=__version__,
        environment=settings.tejasri_env.value,
    )

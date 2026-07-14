"""Patient timeline and audit-history endpoints."""

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from tejasri.api.deps import get_audit_log, get_current_identity, get_timeline_service
from tejasri.application.timeline_service import TimelineService
from tejasri.domain.entities import AuthenticatedIdentity
from tejasri.domain.interfaces import AuditLog

router = APIRouter(tags=["timeline"])


class TimelineEventModel(BaseModel):
    kind: str
    at: datetime
    title: str
    detail: str


class AuditEntryModel(BaseModel):
    audit_id: str
    patient_id: str | None
    actor: str
    action: str
    detail: dict[str, object]
    created_at: datetime


@router.get("/patients/{patient_id}/timeline", response_model=list[TimelineEventModel])
async def patient_timeline(
    patient_id: uuid.UUID,
    identity: Annotated[AuthenticatedIdentity, Depends(get_current_identity)],
    timeline: Annotated[TimelineService, Depends(get_timeline_service)],
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
) -> list[TimelineEventModel]:
    events = await timeline.for_patient(identity, patient_id, limit)
    return [
        TimelineEventModel(kind=e.kind, at=e.at, title=e.title, detail=e.detail) for e in events
    ]


@router.get("/audit", response_model=list[AuditEntryModel])
async def audit_history(
    identity: Annotated[AuthenticatedIdentity, Depends(get_current_identity)],
    audit: Annotated[AuditLog, Depends(get_audit_log)],
    patient_id: uuid.UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[AuditEntryModel]:
    entries = await audit.list_recent(identity.tenant_id, patient_id, limit)
    return [AuditEntryModel(**entry) for entry in entries]  # type: ignore[arg-type]

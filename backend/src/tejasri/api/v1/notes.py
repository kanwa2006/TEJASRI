"""Clinical notes: the agent's long-term semantic memory, over HTTP."""

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from tejasri.api.deps import get_current_identity, get_memory_service
from tejasri.application.memory_service import MemoryService
from tejasri.domain.entities import AuthenticatedIdentity, ClinicalNote

router = APIRouter(prefix="/patients/{patient_id}/notes", tags=["memory"])


class CreateNoteRequest(BaseModel):
    note_text: str = Field(min_length=1, max_length=20_000)


class NoteResponse(BaseModel):
    note_id: uuid.UUID
    note_text: str
    created_at: datetime

    @classmethod
    def from_entity(cls, note: ClinicalNote) -> "NoteResponse":
        return cls(note_id=note.note_id, note_text=note.note_text, created_at=note.created_at)


class RecalledNoteResponse(BaseModel):
    note: NoteResponse
    distance: float


@router.post("", response_model=NoteResponse, status_code=201)
async def create_note(
    patient_id: uuid.UUID,
    body: CreateNoteRequest,
    identity: Annotated[AuthenticatedIdentity, Depends(get_current_identity)],
    memory: Annotated[MemoryService, Depends(get_memory_service)],
) -> NoteResponse:
    note = await memory.add_note(identity, patient_id, body.note_text)
    return NoteResponse.from_entity(note)


@router.get("", response_model=list[NoteResponse])
async def list_notes(
    patient_id: uuid.UUID,
    identity: Annotated[AuthenticatedIdentity, Depends(get_current_identity)],
    memory: Annotated[MemoryService, Depends(get_memory_service)],
) -> list[NoteResponse]:
    notes = await memory.list_recent(identity, patient_id)
    return [NoteResponse.from_entity(n) for n in notes]


@router.get("/recall", response_model=list[RecalledNoteResponse])
async def recall_notes(
    patient_id: uuid.UUID,
    identity: Annotated[AuthenticatedIdentity, Depends(get_current_identity)],
    memory: Annotated[MemoryService, Depends(get_memory_service)],
    q: Annotated[str, Query(min_length=1, max_length=2_000)],
    limit: Annotated[int, Query(ge=1, le=20)] = 5,
) -> list[RecalledNoteResponse]:
    """Semantic recall: nearest clinical notes by meaning (C-SPANN, L2)."""
    recalled = await memory.recall(identity, patient_id, q, limit)
    return [
        RecalledNoteResponse(note=NoteResponse.from_entity(r.note), distance=r.distance)
        for r in recalled
    ]

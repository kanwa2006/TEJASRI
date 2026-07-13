"""Semantic memory use cases: store clinical notes, recall by meaning."""

import uuid

from tejasri.core.errors import ValidationError
from tejasri.domain.entities import AuditEntry, AuthenticatedIdentity, ClinicalNote, RecalledNote
from tejasri.domain.interfaces import AuditLog, ClinicalNoteRepository, EmbeddingProvider

_DEFAULT_RECALL_LIMIT = 5
_MAX_RECALL_LIMIT = 20


class MemoryService:
    def __init__(
        self,
        notes: ClinicalNoteRepository,
        embedder: EmbeddingProvider,
        audit: AuditLog,
    ) -> None:
        self._notes = notes
        self._embedder = embedder
        self._audit = audit

    async def add_note(
        self, identity: AuthenticatedIdentity, patient_id: uuid.UUID, note_text: str
    ) -> ClinicalNote:
        text = note_text.strip()
        if not text:
            raise ValidationError("note text must not be empty")
        embedding = (await self._embedder.embed([text]))[0]
        note = await self._notes.add(identity.tenant_id, patient_id, text, embedding)
        await self._audit.record(
            AuditEntry(
                tenant_id=identity.tenant_id,
                patient_id=patient_id,
                actor=str(identity.user_id),
                action="note.created",
                detail={"note_id": str(note.note_id), "embedder": self._embedder.name},
            )
        )
        return note

    async def recall(
        self,
        identity: AuthenticatedIdentity,
        patient_id: uuid.UUID,
        query: str,
        limit: int = _DEFAULT_RECALL_LIMIT,
    ) -> list[RecalledNote]:
        text = query.strip()
        if not text:
            raise ValidationError("recall query must not be empty")
        limit = min(max(limit, 1), _MAX_RECALL_LIMIT)
        query_embedding = (await self._embedder.embed([text]))[0]
        return await self._notes.recall(identity.tenant_id, patient_id, query_embedding, limit)

    async def list_recent(
        self, identity: AuthenticatedIdentity, patient_id: uuid.UUID, limit: int = 50
    ) -> list[ClinicalNote]:
        return await self._notes.list_recent(identity.tenant_id, patient_id, limit)

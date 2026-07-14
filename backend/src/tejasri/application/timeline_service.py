"""Patient timeline: one chronological view over every kind of memory."""

import uuid
from dataclasses import dataclass
from datetime import datetime

from tejasri.domain.entities import AuthenticatedIdentity
from tejasri.domain.interfaces import (
    AuditLog,
    ClinicalNoteRepository,
    ConversationRepository,
    TaskRepository,
)


@dataclass(frozen=True, slots=True)
class TimelineEvent:
    kind: str  # conversation | note | task | audit
    at: datetime
    title: str
    detail: str


class TimelineService:
    def __init__(
        self,
        conversations: ConversationRepository,
        notes: ClinicalNoteRepository,
        tasks: TaskRepository,
        audit: AuditLog,
    ) -> None:
        self._conversations = conversations
        self._notes = notes
        self._tasks = tasks
        self._audit = audit

    async def for_patient(
        self, identity: AuthenticatedIdentity, patient_id: uuid.UUID, limit: int = 100
    ) -> list[TimelineEvent]:
        tenant_id = identity.tenant_id
        events: list[TimelineEvent] = []

        for message in await self._conversations.recent(tenant_id, patient_id, limit):
            events.append(
                TimelineEvent(
                    kind="conversation",
                    at=message.created_at,
                    title=f"{message.role.value} message",
                    detail=message.content,
                )
            )
        for note in await self._notes.list_recent(tenant_id, patient_id, limit):
            events.append(
                TimelineEvent(
                    kind="note", at=note.created_at, title="clinical note", detail=note.note_text
                )
            )
        for task in await self._tasks.list_for_patient(tenant_id, patient_id):
            events.append(
                TimelineEvent(
                    kind="task",
                    at=task.updated_at,
                    title=f"{task.kind.value} ({task.state.value})",
                    detail=str(task.payload) if task.payload else "",
                )
            )
        for entry in await self._audit.list_recent(tenant_id, patient_id, limit):
            created_at = entry["created_at"]
            assert isinstance(created_at, datetime)  # noqa: S101 — repository contract
            events.append(
                TimelineEvent(
                    kind="audit",
                    at=created_at,
                    title=str(entry["action"]),
                    detail=f"actor: {entry['actor']}",
                )
            )

        events.sort(key=lambda e: e.at, reverse=True)
        return events[:limit]

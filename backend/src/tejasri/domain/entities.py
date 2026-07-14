"""Core domain entities. Pure data — no framework, no I/O."""

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum

from tejasri.domain.safety import Medication


class UserRole(StrEnum):
    PATIENT = "patient"
    CAREGIVER = "caregiver"
    COORDINATOR = "coordinator"
    ADMIN = "admin"


@dataclass(frozen=True, slots=True)
class Tenant:
    tenant_id: uuid.UUID
    name: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class User:
    user_id: uuid.UUID
    tenant_id: uuid.UUID
    email: str
    password_hash: str
    role: UserRole
    display_name: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class Patient:
    patient_id: uuid.UUID
    tenant_id: uuid.UUID
    display_name: str
    external_ref: str | None = None
    dob: date | None = None
    conditions: tuple[str, ...] = ()
    allergies: tuple[str, ...] = ()
    created_at: datetime | None = None


class CarePlanStatus(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"
    CLOSED = "closed"


@dataclass(frozen=True, slots=True)
class CarePlan:
    """The transactional heart of the memory model — versioned, atomic."""

    care_plan_id: uuid.UUID
    tenant_id: uuid.UUID
    patient_id: uuid.UUID
    status: CarePlanStatus
    medications: tuple[Medication, ...]
    version: int
    updated_at: datetime


class TaskKind(StrEnum):
    REFILL = "refill"
    PHARMACIST_REVIEW = "pharmacist_review"
    FOLLOWUP = "followup"
    ADHERENCE_CHECK = "adherence_check"


class TaskState(StrEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    DONE = "done"


# Legal task state-machine transitions. Anything else is a ConflictError.
TASK_TRANSITIONS: dict[TaskState, frozenset[TaskState]] = {
    TaskState.OPEN: frozenset({TaskState.IN_PROGRESS, TaskState.BLOCKED, TaskState.DONE}),
    TaskState.IN_PROGRESS: frozenset({TaskState.BLOCKED, TaskState.DONE}),
    TaskState.BLOCKED: frozenset({TaskState.OPEN, TaskState.IN_PROGRESS}),
    TaskState.DONE: frozenset(),
}


@dataclass(frozen=True, slots=True)
class TaskItem:
    task_id: uuid.UUID
    tenant_id: uuid.UUID
    patient_id: uuid.UUID
    kind: TaskKind
    state: TaskState
    payload: dict[str, object]
    updated_at: datetime


class MessageRole(StrEnum):
    USER = "user"
    AGENT = "agent"
    SYSTEM = "system"


@dataclass(frozen=True, slots=True)
class ConversationMessage:
    """One turn of short-term memory, persisted before anything else happens."""

    message_id: uuid.UUID
    tenant_id: uuid.UUID
    patient_id: uuid.UUID
    role: MessageRole
    content: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class ClinicalNote:
    """Long-term semantic memory: text plus its embedding vector."""

    note_id: uuid.UUID
    tenant_id: uuid.UUID
    patient_id: uuid.UUID
    note_text: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class RecalledNote:
    """A clinical note retrieved by semantic similarity (lower distance = closer)."""

    note: ClinicalNote
    distance: float


@dataclass(frozen=True, slots=True)
class AuditEntry:
    """One accountable action. Append-only; never updated or deleted."""

    tenant_id: uuid.UUID
    actor: str
    action: str
    patient_id: uuid.UUID | None = None
    detail: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class AuthenticatedIdentity:
    """The verified claims a request acts under."""

    user_id: uuid.UUID
    tenant_id: uuid.UUID
    role: UserRole

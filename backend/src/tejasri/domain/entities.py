"""Core domain entities. Pure data — no framework, no I/O."""

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum


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

"""In-memory fakes implementing the domain interfaces for unit tests."""

import uuid
from datetime import UTC, datetime

from tejasri.core.errors import ConflictError
from tejasri.domain.entities import AuditEntry, Patient, Tenant, User, UserRole


class FakeTenantRepository:
    def __init__(self) -> None:
        self.tenants: dict[uuid.UUID, Tenant] = {}

    async def create(self, name: str) -> Tenant:
        if any(t.name == name for t in self.tenants.values()):
            raise ConflictError(f"tenant name already exists: {name}")
        tenant = Tenant(tenant_id=uuid.uuid4(), name=name, created_at=datetime.now(UTC))
        self.tenants[tenant.tenant_id] = tenant
        return tenant

    async def get(self, tenant_id: uuid.UUID) -> Tenant | None:
        return self.tenants.get(tenant_id)


class FakeUserRepository:
    def __init__(self) -> None:
        self.users: dict[uuid.UUID, User] = {}

    async def create(
        self,
        tenant_id: uuid.UUID,
        email: str,
        password_hash: str,
        role: UserRole,
        display_name: str,
    ) -> User:
        if any(u.email == email.lower() for u in self.users.values()):
            raise ConflictError(f"email already registered: {email}")
        user = User(
            user_id=uuid.uuid4(),
            tenant_id=tenant_id,
            email=email.lower(),
            password_hash=password_hash,
            role=role,
            display_name=display_name,
            created_at=datetime.now(UTC),
        )
        self.users[user.user_id] = user
        return user

    async def get_by_email(self, email: str) -> User | None:
        return next((u for u in self.users.values() if u.email == email.lower()), None)


class FakePatientRepository:
    def __init__(self) -> None:
        self.patients: dict[uuid.UUID, Patient] = {}

    async def create(self, patient: Patient) -> Patient:
        stored = Patient(
            patient_id=uuid.uuid4(),
            tenant_id=patient.tenant_id,
            display_name=patient.display_name,
            external_ref=patient.external_ref,
            dob=patient.dob,
            conditions=patient.conditions,
            allergies=patient.allergies,
            created_at=datetime.now(UTC),
        )
        self.patients[stored.patient_id] = stored
        return stored

    async def get(self, tenant_id: uuid.UUID, patient_id: uuid.UUID) -> Patient | None:
        patient = self.patients.get(patient_id)
        if patient is None or patient.tenant_id != tenant_id:
            return None
        return patient

    async def list_for_tenant(self, tenant_id: uuid.UUID) -> list[Patient]:
        return [p for p in self.patients.values() if p.tenant_id == tenant_id]


class FakeAuditLog:
    def __init__(self) -> None:
        self.entries: list[AuditEntry] = []

    async def record(self, entry: AuditEntry) -> None:
        self.entries.append(entry)

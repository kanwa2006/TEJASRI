"""Domain interfaces (ports). Infrastructure implements these Protocols;
application services depend on them, never on concrete adapters."""

import uuid
from typing import Protocol

from tejasri.domain.entities import AuditEntry, Patient, Tenant, User, UserRole


class TenantRepository(Protocol):
    async def create(self, name: str) -> Tenant: ...
    async def get(self, tenant_id: uuid.UUID) -> Tenant | None: ...


class UserRepository(Protocol):
    async def create(
        self,
        tenant_id: uuid.UUID,
        email: str,
        password_hash: str,
        role: UserRole,
        display_name: str,
    ) -> User: ...
    async def get_by_email(self, email: str) -> User | None: ...


class PatientRepository(Protocol):
    async def create(self, patient: Patient) -> Patient: ...
    async def get(self, tenant_id: uuid.UUID, patient_id: uuid.UUID) -> Patient | None: ...
    async def list_for_tenant(self, tenant_id: uuid.UUID) -> list[Patient]: ...


class AuditLog(Protocol):
    async def record(self, entry: AuditEntry) -> None: ...


class PasswordHasher(Protocol):
    def hash(self, password: str) -> str: ...
    def verify(self, password: str, password_hash: str) -> bool: ...


class TokenIssuer(Protocol):
    def issue(self, user_id: uuid.UUID, tenant_id: uuid.UUID, role: UserRole) -> str: ...
    def verify(self, token: str) -> tuple[uuid.UUID, uuid.UUID, UserRole]:
        """Return (user_id, tenant_id, role) or raise AuthenticationError."""
        ...

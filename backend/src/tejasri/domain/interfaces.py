"""Domain interfaces (ports). Infrastructure implements these Protocols;
application services depend on them, never on concrete adapters."""

import uuid
from typing import Protocol

from tejasri.domain.entities import (
    AuditEntry,
    ClinicalNote,
    ConversationMessage,
    MessageRole,
    Patient,
    RecalledNote,
    Tenant,
    User,
    UserRole,
)

EMBEDDING_DIM = 384  # matches VECTOR(384) in the schema; changing it is a migration


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


class EmbeddingProvider(Protocol):
    """Turns text into EMBEDDING_DIM-dimensional unit vectors.

    Kept separate from LLMProvider deliberately (ADR 0003): embeddings are
    load-bearing memory and must stay deterministic and locally computable.
    """

    name: str

    async def embed(self, texts: list[str]) -> list[list[float]]: ...


class LLMProvider(Protocol):
    """Text generation only. The LLM explains; it never decides (ADR 0004)."""

    name: str

    async def generate(self, system: str, messages: list[dict[str, str]]) -> str:
        """messages: [{"role": "user"|"assistant", "content": ...}]. Raises
        ExternalServiceError on provider failure so callers can fail over."""
        ...


class ClinicalNoteRepository(Protocol):
    async def add(
        self,
        tenant_id: uuid.UUID,
        patient_id: uuid.UUID,
        note_text: str,
        embedding: list[float],
    ) -> ClinicalNote: ...
    async def recall(
        self,
        tenant_id: uuid.UUID,
        patient_id: uuid.UUID,
        query_embedding: list[float],
        limit: int,
    ) -> list[RecalledNote]: ...
    async def list_recent(
        self, tenant_id: uuid.UUID, patient_id: uuid.UUID, limit: int
    ) -> list[ClinicalNote]: ...


class ConversationRepository(Protocol):
    async def append(
        self,
        tenant_id: uuid.UUID,
        patient_id: uuid.UUID,
        role: MessageRole,
        content: str,
    ) -> ConversationMessage: ...
    async def recent(
        self, tenant_id: uuid.UUID, patient_id: uuid.UUID, limit: int
    ) -> list[ConversationMessage]: ...


class PasswordHasher(Protocol):
    def hash(self, password: str) -> str: ...
    def verify(self, password: str, password_hash: str) -> bool: ...


class TokenIssuer(Protocol):
    def issue(self, user_id: uuid.UUID, tenant_id: uuid.UUID, role: UserRole) -> str: ...
    def verify(self, token: str) -> tuple[uuid.UUID, uuid.UUID, UserRole]:
        """Return (user_id, tenant_id, role) or raise AuthenticationError."""
        ...

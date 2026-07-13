"""Long-term semantic memory and conversation history repositories.

Vectors travel as pgvector text literals ('[0.1,0.2,...]') cast with
::VECTOR in SQL — parameterized, never string-concatenated into queries.
Recall uses L2 distance (<->), the only operator supported by C-SPANN in
preview, with tenant/patient prefix columns so search cost scales with
one patient's history, not the whole table.
"""

import uuid
from typing import Any

from tejasri.domain.entities import ClinicalNote, ConversationMessage, MessageRole, RecalledNote
from tejasri.infrastructure.db import Database


def _vector_literal(embedding: list[float]) -> str:
    return "[" + ",".join(f"{v:.8f}" for v in embedding) + "]"


def _note_from_row(row: Any) -> ClinicalNote:
    return ClinicalNote(
        note_id=row["note_id"],
        tenant_id=row["tenant_id"],
        patient_id=row["patient_id"],
        note_text=row["note_text"],
        created_at=row["created_at"],
    )


class CockroachClinicalNoteRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    async def add(
        self,
        tenant_id: uuid.UUID,
        patient_id: uuid.UUID,
        note_text: str,
        embedding: list[float],
    ) -> ClinicalNote:
        async with self._db.tenant_connection(tenant_id) as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO clinical_notes (tenant_id, patient_id, note_text, embedding)
                VALUES ($1, $2, $3, $4::VECTOR)
                RETURNING note_id, tenant_id, patient_id, note_text, created_at
                """,
                tenant_id,
                patient_id,
                note_text,
                _vector_literal(embedding),
            )
        return _note_from_row(row)

    async def recall(
        self,
        tenant_id: uuid.UUID,
        patient_id: uuid.UUID,
        query_embedding: list[float],
        limit: int,
    ) -> list[RecalledNote]:
        async with self._db.tenant_connection(tenant_id) as conn:
            rows = await conn.fetch(
                """
                SELECT note_id, tenant_id, patient_id, note_text, created_at,
                       embedding <-> $3::VECTOR AS distance
                FROM clinical_notes
                WHERE tenant_id = $1 AND patient_id = $2
                ORDER BY embedding <-> $3::VECTOR
                LIMIT $4
                """,
                tenant_id,
                patient_id,
                _vector_literal(query_embedding),
                limit,
            )
        return [RecalledNote(note=_note_from_row(r), distance=float(r["distance"])) for r in rows]

    async def list_recent(
        self, tenant_id: uuid.UUID, patient_id: uuid.UUID, limit: int
    ) -> list[ClinicalNote]:
        async with self._db.tenant_connection(tenant_id) as conn:
            rows = await conn.fetch(
                """
                SELECT note_id, tenant_id, patient_id, note_text, created_at
                FROM clinical_notes
                WHERE tenant_id = $1 AND patient_id = $2
                ORDER BY created_at DESC
                LIMIT $3
                """,
                tenant_id,
                patient_id,
                limit,
            )
        return [_note_from_row(r) for r in rows]


class CockroachConversationRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    async def append(
        self,
        tenant_id: uuid.UUID,
        patient_id: uuid.UUID,
        role: MessageRole,
        content: str,
    ) -> ConversationMessage:
        async with self._db.tenant_connection(tenant_id) as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO conversations (tenant_id, patient_id, role, content)
                VALUES ($1, $2, $3, $4)
                RETURNING *
                """,
                tenant_id,
                patient_id,
                role.value,
                content,
            )
        assert row is not None  # noqa: S101 — INSERT..RETURNING always yields a row
        return ConversationMessage(
            message_id=row["message_id"],
            tenant_id=row["tenant_id"],
            patient_id=row["patient_id"],
            role=MessageRole(row["role"]),
            content=row["content"],
            created_at=row["created_at"],
        )

    async def recent(
        self, tenant_id: uuid.UUID, patient_id: uuid.UUID, limit: int
    ) -> list[ConversationMessage]:
        async with self._db.tenant_connection(tenant_id) as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM (
                    SELECT * FROM conversations
                    WHERE tenant_id = $1 AND patient_id = $2
                    ORDER BY created_at DESC LIMIT $3
                ) ORDER BY created_at ASC
                """,
                tenant_id,
                patient_id,
                limit,
            )
        return [
            ConversationMessage(
                message_id=r["message_id"],
                tenant_id=r["tenant_id"],
                patient_id=r["patient_id"],
                role=MessageRole(r["role"]),
                content=r["content"],
                created_at=r["created_at"],
            )
            for r in rows
        ]

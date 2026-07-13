"""Semantic memory against the real memory layer: store → recall by meaning."""

import uuid

import pytest

from tejasri.domain.entities import MessageRole, Patient
from tejasri.infrastructure.db import Database
from tejasri.infrastructure.embeddings import HashingEmbedder
from tejasri.infrastructure.repositories.accounts import CockroachTenantRepository
from tejasri.infrastructure.repositories.memory import (
    CockroachClinicalNoteRepository,
    CockroachConversationRepository,
)
from tejasri.infrastructure.repositories.patients import CockroachPatientRepository

pytestmark = pytest.mark.integration


async def _seed_patient(db: Database) -> tuple[uuid.UUID, uuid.UUID]:
    tenant = await CockroachTenantRepository(db).create(f"memclinic-{uuid.uuid4()}")
    patient = await CockroachPatientRepository(db).create(
        Patient(patient_id=uuid.uuid4(), tenant_id=tenant.tenant_id, display_name="Asha Rao")
    )
    return tenant.tenant_id, patient.patient_id


async def test_vector_recall_returns_semantically_closest_note(db: Database) -> None:
    tenant_id, patient_id = await _seed_patient(db)
    notes = CockroachClinicalNoteRepository(db)
    embedder = HashingEmbedder()

    texts = [
        "Patient started metformin 500mg twice daily for type 2 diabetes.",
        "Reported mild ankle sprain after morning walk; advised rest and ice.",
        "Blood pressure stable at 120/80; continue current lisinopril dose.",
    ]
    for text, embedding in zip(texts, await embedder.embed(texts), strict=True):
        await notes.add(tenant_id, patient_id, text, embedding)

    query_embedding = (await embedder.embed(["diabetes medication metformin dosage"]))[0]
    recalled = await notes.recall(tenant_id, patient_id, query_embedding, limit=2)

    assert len(recalled) == 2
    assert "metformin" in recalled[0].note.note_text
    assert recalled[0].distance <= recalled[1].distance


async def test_notes_are_tenant_isolated_in_vector_search(db: Database) -> None:
    tenant_a, patient_a = await _seed_patient(db)
    tenant_b, patient_b = await _seed_patient(db)
    notes = CockroachClinicalNoteRepository(db)
    embedder = HashingEmbedder()

    (embedding,) = await embedder.embed(["confidential note for tenant A"])
    await notes.add(tenant_a, patient_a, "confidential note for tenant A", embedding)

    # Same query, other tenant: RLS + prefix columns yield nothing.
    recalled = await notes.recall(tenant_b, patient_b, embedding, limit=5)
    assert recalled == []


async def test_conversation_history_round_trips_in_order(db: Database) -> None:
    tenant_id, patient_id = await _seed_patient(db)
    conversations = CockroachConversationRepository(db)

    await conversations.append(tenant_id, patient_id, MessageRole.USER, "Did I take my dose?")
    await conversations.append(tenant_id, patient_id, MessageRole.AGENT, "Yes, this morning.")

    history = await conversations.recent(tenant_id, patient_id, limit=10)
    assert [m.role for m in history] == [MessageRole.USER, MessageRole.AGENT]
    assert history[0].content == "Did I take my dose?"

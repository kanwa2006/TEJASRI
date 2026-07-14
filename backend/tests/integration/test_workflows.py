"""Care plans and the agent turn against the real memory layer.

Includes the concurrency proof: two agents updating the same care plan
either serialize cleanly or one gets a clean version conflict — nothing
is ever silently lost.
"""

import asyncio
import uuid

import pytest

from tejasri.application.agent_service import AgentService
from tejasri.core.errors import ConflictError, ExternalServiceError
from tejasri.domain.entities import AuthenticatedIdentity, Patient, UserRole
from tejasri.domain.safety import Medication, SafetyEngine
from tejasri.infrastructure.db import Database
from tejasri.infrastructure.embeddings import HashingEmbedder
from tejasri.infrastructure.repositories.accounts import CockroachTenantRepository
from tejasri.infrastructure.repositories.memory import (
    CockroachClinicalNoteRepository,
    CockroachConversationRepository,
)
from tejasri.infrastructure.repositories.patients import (
    CockroachAuditLog,
    CockroachPatientRepository,
)
from tejasri.infrastructure.repositories.workflows import (
    CockroachCarePlanRepository,
)
from tejasri.infrastructure.safety_data import load_default_dataset

pytestmark = pytest.mark.integration


class DownLLM:
    name = "down"

    async def generate(self, system: str, messages: list[dict[str, str]]) -> str:
        raise ExternalServiceError("down for the resilience demo")


async def _seed(db: Database) -> tuple[AuthenticatedIdentity, uuid.UUID]:
    tenant = await CockroachTenantRepository(db).create(f"wf-{uuid.uuid4()}")
    patient = await CockroachPatientRepository(db).create(
        Patient(
            patient_id=uuid.uuid4(),
            tenant_id=tenant.tenant_id,
            display_name="Asha Rao",
            allergies=("penicillin",),
        )
    )
    identity = AuthenticatedIdentity(
        user_id=uuid.uuid4(), tenant_id=tenant.tenant_id, role=UserRole.COORDINATOR
    )
    return identity, patient.patient_id


async def test_care_plan_versioned_update_roundtrip(db: Database) -> None:
    identity, patient_id = await _seed(db)
    plans = CockroachCarePlanRepository(db)

    plan = await plans.get_or_create(identity.tenant_id, patient_id)
    assert plan.version == 1

    updated = await plans.update_medications(
        identity.tenant_id,
        patient_id,
        [Medication(name="metformin", dose="500mg", schedule="twice daily")],
        expected_version=1,
    )
    assert updated.version == 2
    assert updated.medications[0].name == "metformin"


async def test_stale_version_gets_clean_conflict(db: Database) -> None:
    identity, patient_id = await _seed(db)
    plans = CockroachCarePlanRepository(db)
    await plans.get_or_create(identity.tenant_id, patient_id)
    await plans.update_medications(
        identity.tenant_id, patient_id, [Medication(name="metformin")], expected_version=1
    )
    with pytest.raises(ConflictError, match="version conflict"):
        await plans.update_medications(
            identity.tenant_id, patient_id, [Medication(name="aspirin")], expected_version=1
        )


async def test_concurrent_updates_never_lose_state(db: Database) -> None:
    """Two agents race on the same plan: exactly one write per version wins,
    the loser sees a conflict, and the final version count is exact."""
    identity, patient_id = await _seed(db)
    plans = CockroachCarePlanRepository(db)
    await plans.get_or_create(identity.tenant_id, patient_id)

    async def contender(name: str) -> str | None:
        try:
            await plans.update_medications(
                identity.tenant_id, patient_id, [Medication(name=name)], expected_version=1
            )
            return name
        except ConflictError:
            return None

    winners = [
        w
        for w in await asyncio.gather(contender("metformin"), contender("aspirin"))
        if w is not None
    ]
    assert len(winners) == 1  # exactly one writer won; no silent overwrite

    final = await plans.get_or_create(identity.tenant_id, patient_id)
    assert final.version == 2
    assert final.medications[0].name == winners[0]


async def test_agent_turn_end_to_end_with_llm_down(db: Database) -> None:
    """The full turn against real memory with every LLM unavailable:
    evidence recalled, safety checked, deterministic answer, all persisted."""
    identity, patient_id = await _seed(db)
    notes = CockroachClinicalNoteRepository(db)
    embedder = HashingEmbedder()
    text = "Started metformin 500mg twice daily for type 2 diabetes."
    await notes.add(identity.tenant_id, patient_id, text, (await embedder.embed([text]))[0])

    plans = CockroachCarePlanRepository(db)
    await plans.get_or_create(identity.tenant_id, patient_id)
    await plans.update_medications(
        identity.tenant_id, patient_id, [Medication(name="metformin")], expected_version=1
    )

    agent = AgentService(
        conversations=CockroachConversationRepository(db),
        notes=notes,
        plans=plans,
        patients=CockroachPatientRepository(db),
        embedder=embedder,
        llm=DownLLM(),
        safety=SafetyEngine(load_default_dataset()),
        audit=CockroachAuditLog(db),
    )
    result = await agent.handle_turn(identity, patient_id, "what diabetes medication am I on?")

    assert result.degraded and result.provider == "deterministic-template"
    assert "metformin" in result.answer
    assert result.evidence and "metformin" in result.evidence[0].note.note_text

    history = await CockroachConversationRepository(db).recent(identity.tenant_id, patient_id, 10)
    assert len(history) == 2  # user + agent, both durable
    audit_rows = await CockroachAuditLog(db).list_recent(identity.tenant_id, patient_id, 10)
    assert any(r["action"] == "agent.turn" for r in audit_rows)

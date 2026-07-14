"""AgentService: memory first, safety authoritative, graceful degradation."""

import uuid
from datetime import UTC, datetime

from tejasri.application.agent_service import AgentService
from tejasri.core.errors import ExternalServiceError
from tejasri.domain.entities import (
    AuthenticatedIdentity,
    CarePlan,
    CarePlanStatus,
    ClinicalNote,
    MessageRole,
    RecalledNote,
    UserRole,
)
from tejasri.domain.safety import Medication, SafetyEngine
from tejasri.infrastructure.embeddings import HashingEmbedder
from tejasri.infrastructure.safety_data import load_default_dataset
from tests.unit.fakes import FakeAuditLog, FakePatientRepository


class FakeConversations:
    def __init__(self) -> None:
        self.messages: list[tuple[MessageRole, str]] = []

    async def append(
        self, tenant_id: uuid.UUID, patient_id: uuid.UUID, role: MessageRole, content: str
    ) -> object:
        self.messages.append((role, content))
        return None

    async def recent(self, tenant_id: uuid.UUID, patient_id: uuid.UUID, limit: int) -> list:
        return []


class FakeNotes:
    def __init__(self, texts: list[str]) -> None:
        self._texts = texts

    async def add(self, *args: object, **kw: object) -> object:
        raise NotImplementedError

    async def recall(
        self,
        tenant_id: uuid.UUID,
        patient_id: uuid.UUID,
        query_embedding: list[float],
        limit: int,
    ) -> list[RecalledNote]:
        return [
            RecalledNote(
                note=ClinicalNote(
                    note_id=uuid.uuid4(),
                    tenant_id=tenant_id,
                    patient_id=patient_id,
                    note_text=text,
                    created_at=datetime.now(UTC),
                ),
                distance=0.4,
            )
            for text in self._texts[:limit]
        ]

    async def list_recent(self, *args: object) -> list:
        return []


class FakePlans:
    def __init__(self, medications: list[Medication]) -> None:
        self._medications = medications

    async def get_or_create(self, tenant_id: uuid.UUID, patient_id: uuid.UUID) -> CarePlan:
        return CarePlan(
            care_plan_id=uuid.uuid4(),
            tenant_id=tenant_id,
            patient_id=patient_id,
            status=CarePlanStatus.ACTIVE,
            medications=tuple(self._medications),
            version=3,
            updated_at=datetime.now(UTC),
        )

    async def update_medications(self, *args: object, **kw: object) -> CarePlan:
        raise NotImplementedError


class ScriptedLLM:
    def __init__(self, answer: str | None) -> None:
        self._answer = answer
        self.name = "scripted"

    async def generate(self, system: str, messages: list[dict[str, str]]) -> str:
        if self._answer is None:
            raise ExternalServiceError("scripted outage")
        return self._answer


def make_agent(
    llm_answer: str | None,
    medications: list[Medication],
) -> tuple[AgentService, FakeConversations, FakeAuditLog, AuthenticatedIdentity, uuid.UUID]:
    conversations = FakeConversations()
    audit = FakeAuditLog()
    identity = AuthenticatedIdentity(
        user_id=uuid.uuid4(), tenant_id=uuid.uuid4(), role=UserRole.COORDINATOR
    )
    agent = AgentService(
        conversations=conversations,
        notes=FakeNotes(["Started metformin for type 2 diabetes."]),
        plans=FakePlans(medications),
        patients=FakePatientRepository(),  # unknown patient -> no recorded allergies
        embedder=HashingEmbedder(),
        llm=ScriptedLLM(llm_answer),
        safety=SafetyEngine(load_default_dataset()),
        audit=audit,
    )
    return agent, conversations, audit, identity, uuid.uuid4()


async def test_turn_persists_both_messages_and_audits() -> None:
    agent, conversations, audit, identity, patient_id = make_agent(
        "You are on metformin.", [Medication(name="metformin")]
    )
    result = await agent.handle_turn(identity, patient_id, "What am I taking?")

    roles = [r for r, _ in conversations.messages]
    assert roles == [MessageRole.USER, MessageRole.AGENT]
    assert result.answer.startswith("You are on metformin.")
    assert any(e.action == "agent.turn" for e in audit.entries)
    assert result.evidence and result.retrieval_confidence > 0


async def test_disclosure_is_enforced_when_llm_omits_a_flag() -> None:
    agent, _, _, identity, patient_id = make_agent(
        "Everything looks fine!",  # LLM wrongly omits the warfarin+ibuprofen flag
        [Medication(name="warfarin"), Medication(name="ibuprofen")],
    )
    result = await agent.handle_turn(identity, patient_id, "Can I take my meds together?")

    assert result.disclosure_enforced
    assert "Safety notices" in result.answer
    assert "warfarin" in result.answer.lower()


async def test_llm_that_discloses_is_not_modified() -> None:
    honest = "Warning: warfarin with ibuprofen increases bleeding risk (major)."
    agent, _, _, identity, patient_id = make_agent(
        honest, [Medication(name="warfarin"), Medication(name="ibuprofen")]
    )
    result = await agent.handle_turn(identity, patient_id, "Is this safe?")
    assert result.answer == honest
    assert not result.disclosure_enforced


async def test_total_llm_outage_degrades_to_deterministic_answer() -> None:
    agent, conversations, audit, identity, patient_id = make_agent(
        None, [Medication(name="metformin")]
    )
    result = await agent.handle_turn(identity, patient_id, "What am I taking?")

    assert result.degraded
    assert result.provider == "deterministic-template"
    assert "metformin" in result.answer
    # Memory still wrote both sides of the conversation.
    assert len(conversations.messages) == 2

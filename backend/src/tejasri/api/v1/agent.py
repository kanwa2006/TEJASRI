"""The agent conversation endpoint — explainable by construction.

Every turn returns the full evidence chain: what was recalled, what the
deterministic safety engine found, which provider answered, and how
confident retrieval was. No black-box recommendations.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from tejasri.api.deps import get_agent_service, get_conversation_repository, get_current_identity
from tejasri.api.v1.care_plans import SafetyReportModel
from tejasri.application.agent_service import AgentService, AgentTurnResult
from tejasri.core.metrics import metrics
from tejasri.domain.entities import AuthenticatedIdentity
from tejasri.domain.interfaces import ConversationRepository

router = APIRouter(tags=["agent"])


class AgentTurnRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4_000)


class EvidenceModel(BaseModel):
    note_id: uuid.UUID
    note_text: str
    distance: float


class AgentTurnResponse(BaseModel):
    answer: str
    safety: SafetyReportModel
    evidence: list[EvidenceModel]
    care_plan_version: int
    provider: str
    degraded: bool
    retrieval_confidence: float
    disclosure_enforced: bool

    @classmethod
    def from_result(cls, result: AgentTurnResult) -> "AgentTurnResponse":
        return cls(
            answer=result.answer,
            safety=SafetyReportModel.from_domain(result.safety),
            evidence=[
                EvidenceModel(
                    note_id=e.note.note_id, note_text=e.note.note_text, distance=e.distance
                )
                for e in result.evidence
            ],
            care_plan_version=result.care_plan_version,
            provider=result.provider,
            degraded=result.degraded,
            retrieval_confidence=result.retrieval_confidence,
            disclosure_enforced=result.disclosure_enforced,
        )


class ConversationMessageModel(BaseModel):
    message_id: uuid.UUID
    role: str
    content: str
    created_at: str


@router.post("/patients/{patient_id}/agent/turn", response_model=AgentTurnResponse)
async def agent_turn(
    patient_id: uuid.UUID,
    body: AgentTurnRequest,
    identity: Annotated[AuthenticatedIdentity, Depends(get_current_identity)],
    agent: Annotated[AgentService, Depends(get_agent_service)],
) -> AgentTurnResponse:
    result = await agent.handle_turn(identity, patient_id, body.message)
    metrics.observe_agent_turn(result.provider, result.degraded, len(result.safety.flags))
    return AgentTurnResponse.from_result(result)


@router.get("/patients/{patient_id}/conversation", response_model=list[ConversationMessageModel])
async def conversation_history(
    patient_id: uuid.UUID,
    identity: Annotated[AuthenticatedIdentity, Depends(get_current_identity)],
    conversations: Annotated[ConversationRepository, Depends(get_conversation_repository)],
    limit: int = 50,
) -> list[ConversationMessageModel]:
    messages = await conversations.recent(identity.tenant_id, patient_id, min(limit, 200))
    return [
        ConversationMessageModel(
            message_id=m.message_id,
            role=m.role.value,
            content=m.content,
            created_at=m.created_at.isoformat(),
        )
        for m in messages
    ]

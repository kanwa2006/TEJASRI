"""The agent orchestrator — one memory-aware, safety-first conversation turn.

The turn order is the safety architecture (blueprint Part C):

1. Persist the user message (memory first — a crash after this point
   loses nothing).
2. Recall relevant clinical notes by meaning (C-SPANN vector search).
3. Load the care plan and run the DETERMINISTIC safety engine.
4. Ask the LLM to explain — given the verdict, never to produce one.
5. Enforce disclosure: every flag the engine raised must appear in the
   answer; if the LLM omitted any, a standardized disclosure is appended.
6. If every LLM provider is down, degrade to a deterministic template
   answer built from the same evidence — reduced eloquence, zero loss of
   safety or memory.
7. Persist the agent message and audit the entire turn.
"""

import uuid
from dataclasses import dataclass, field

from tejasri.core.errors import ExternalServiceError
from tejasri.core.logging import get_logger
from tejasri.domain.entities import (
    AuditEntry,
    AuthenticatedIdentity,
    CarePlan,
    MessageRole,
    RecalledNote,
)
from tejasri.domain.interfaces import (
    AuditLog,
    CarePlanRepository,
    ClinicalNoteRepository,
    ConversationRepository,
    EmbeddingProvider,
    LLMProvider,
    PatientRepository,
)
from tejasri.domain.safety import SafetyEngine, SafetyReport

log = get_logger(__name__)

SYSTEM_PROMPT = """You are Aarogya, the care-continuity assistant of TEJASRI.

Hard rules — you must follow every one:
1. You are an assistive tool, NOT a medical professional. Never diagnose,
   never prescribe, never adjust doses.
2. A deterministic safety engine has already checked this patient's
   medications. Its verdict is included below and is AUTHORITATIVE. You may
   explain it in plain language. You must never contradict it, soften a
   severity, or invent interactions it did not report.
3. Ground your answer in the patient's care plan and the retrieved
   history excerpts provided. If the context does not contain the answer,
   say so plainly instead of guessing.
4. Recommend consulting the care team for any decision that changes
   treatment.
5. Be warm, calm, and concise."""

_RECALL_LIMIT = 5
_HISTORY_LIMIT = 10


@dataclass(frozen=True, slots=True)
class AgentTurnResult:
    answer: str
    safety: SafetyReport
    evidence: list[RecalledNote]
    care_plan_version: int
    provider: str  # which LLM answered, or "deterministic-template"
    degraded: bool  # True when no LLM was reachable
    retrieval_confidence: float  # 0..1, from vector distances — labeled honestly
    disclosure_enforced: bool = field(default=False)


class AgentService:
    def __init__(
        self,
        conversations: ConversationRepository,
        notes: ClinicalNoteRepository,
        plans: CarePlanRepository,
        patients: PatientRepository,
        embedder: EmbeddingProvider,
        llm: LLMProvider,
        safety: SafetyEngine,
        audit: AuditLog,
    ) -> None:
        self._conversations = conversations
        self._notes = notes
        self._plans = plans
        self._patients = patients
        self._embedder = embedder
        self._llm = llm
        self._safety = safety
        self._audit = audit

    async def handle_turn(
        self, identity: AuthenticatedIdentity, patient_id: uuid.UUID, user_message: str
    ) -> AgentTurnResult:
        tenant_id = identity.tenant_id

        # 1. Memory first.
        await self._conversations.append(tenant_id, patient_id, MessageRole.USER, user_message)

        # 2. Semantic recall.
        query_embedding = (await self._embedder.embed([user_message]))[0]
        evidence = await self._notes.recall(tenant_id, patient_id, query_embedding, _RECALL_LIMIT)

        # 3. Deterministic safety — authoritative.
        plan = await self._plans.get_or_create(tenant_id, patient_id)
        patient = await self._patients.get(tenant_id, patient_id)
        allergies = list(patient.allergies) if patient else []
        safety = self._safety.check(list(plan.medications), allergies)

        # 4. LLM explains (or 6. deterministic degradation).
        history = await self._conversations.recent(tenant_id, patient_id, _HISTORY_LIMIT)
        context = self._build_context(user_message, plan, evidence, safety)
        messages = [
            *(
                {
                    "role": "assistant" if m.role is MessageRole.AGENT else "user",
                    "content": m.content,
                }
                for m in history[:-1]  # the latest user message is inside `context`
            ),
            {"role": "user", "content": context},
        ]
        degraded = False
        provider = getattr(self._llm, "name", "llm")
        try:
            answer = await self._llm.generate(SYSTEM_PROMPT, messages)
        except ExternalServiceError as exc:
            log.warning("agent_degraded_mode", error=exc.message)
            answer = self._template_answer(plan, evidence, safety)
            provider = "deterministic-template"
            degraded = True

        # 5. Disclosure enforcement — the engine's flags always surface.
        answer, disclosure_enforced = self._enforce_disclosure(answer, safety)

        # 7. Persist and audit.
        await self._conversations.append(tenant_id, patient_id, MessageRole.AGENT, answer)
        await self._audit.record(
            AuditEntry(
                tenant_id=tenant_id,
                patient_id=patient_id,
                actor="agent",
                action="agent.turn",
                detail={
                    "provider": provider,
                    "degraded": degraded,
                    "recalled_notes": [str(e.note.note_id) for e in evidence],
                    "safety_flags": [f.description for f in safety.flags],
                    "dataset_version": safety.dataset_version,
                    "care_plan_version": plan.version,
                    "disclosure_enforced": disclosure_enforced,
                },
            )
        )
        return AgentTurnResult(
            answer=answer,
            safety=safety,
            evidence=evidence,
            care_plan_version=plan.version,
            provider=provider,
            degraded=degraded,
            retrieval_confidence=self._retrieval_confidence(evidence),
            disclosure_enforced=disclosure_enforced,
        )

    @staticmethod
    def _build_context(
        user_message: str,
        plan: CarePlan,
        evidence: list[RecalledNote],
        safety: SafetyReport,
    ) -> str:
        medications = (
            "\n".join(f"- {m.name} {m.dose} {m.schedule}".rstrip() for m in plan.medications)
            or "- (no active medications)"
        )
        excerpts = (
            "\n".join(f"- {e.note.note_text}" for e in evidence) or "- (no relevant history found)"
        )
        if safety.has_flags:
            verdict = "\n".join(
                f"- [{(f.severity.value if f.severity else 'review').upper()}] "
                f"{f.description} (source: {f.source})"
                for f in safety.flags
            )
        else:
            verdict = (
                f"- No interactions or allergy conflicts found across "
                f"{safety.checked_pairs} checked pairs (dataset {safety.dataset_version})."
            )
        return (
            f"CURRENT CARE PLAN (version {plan.version}):\n{medications}\n\n"
            f"RETRIEVED HISTORY (by semantic similarity):\n{excerpts}\n\n"
            f"DETERMINISTIC SAFETY VERDICT (authoritative):\n{verdict}\n\n"
            f"PATIENT MESSAGE:\n{user_message}"
        )

    @staticmethod
    def _template_answer(plan: CarePlan, evidence: list[RecalledNote], safety: SafetyReport) -> str:
        """Deterministic answer used when no LLM is reachable. Same evidence,
        same safety verdict — the platform never goes silent."""
        lines = [
            "(Automated summary — the language model is temporarily unavailable, "
            "so this response was assembled directly from your records.)",
            "",
            f"Your care plan (version {plan.version}) lists: "
            + (", ".join(m.name for m in plan.medications) or "no active medications")
            + ".",
        ]
        if evidence:
            lines += ["", "Most relevant history:"]
            lines += [f"- {e.note.note_text}" for e in evidence[:3]]
        lines += ["", "Please consult your care team before making any treatment changes."]
        return "\n".join(lines)

    @staticmethod
    def _enforce_disclosure(answer: str, safety: SafetyReport) -> tuple[str, bool]:
        """Every engine flag must be visible in the final answer. If the LLM
        omitted any flagged drug, append the standardized disclosure block."""
        if not safety.has_flags:
            return answer, False
        lowered = answer.lower()
        missing = [
            flag for flag in safety.flags if not all(drug.lower() in lowered for drug in flag.drugs)
        ]
        if not missing:
            return answer, False
        disclosure = ["", "---", "⚠ Safety notices (deterministic check):"]
        disclosure += [
            f"- [{(f.severity.value if f.severity else 'review').upper()}] "
            f"{f.description} (source: {f.source})"
            for f in missing
        ]
        return answer + "\n".join(disclosure), True

    @staticmethod
    def _retrieval_confidence(evidence: list[RecalledNote]) -> float:
        """Map best L2 distance (unit vectors: 0..2) to a 0..1 score."""
        if not evidence:
            return 0.0
        best = min(e.distance for e in evidence)
        return round(max(0.0, min(1.0, 1.0 - best / 2.0)), 3)

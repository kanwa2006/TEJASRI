"""Care-plan use cases: safety-checked, human-confirmed, versioned, audited."""

import uuid
from dataclasses import dataclass

from tejasri.core.errors import ValidationError
from tejasri.domain.entities import AuditEntry, AuthenticatedIdentity, CarePlan
from tejasri.domain.interfaces import AuditLog, CarePlanRepository, PatientRepository
from tejasri.domain.safety import Medication, SafetyEngine, SafetyReport


@dataclass(frozen=True, slots=True)
class CarePlanUpdateResult:
    plan: CarePlan
    safety: SafetyReport
    applied: bool


class CarePlanService:
    def __init__(
        self,
        plans: CarePlanRepository,
        patients: PatientRepository,
        safety: SafetyEngine,
        audit: AuditLog,
    ) -> None:
        self._plans = plans
        self._patients = patients
        self._safety = safety
        self._audit = audit

    async def get_plan(
        self, identity: AuthenticatedIdentity, patient_id: uuid.UUID
    ) -> tuple[CarePlan, SafetyReport]:
        """The plan is always returned WITH its current safety verdict."""
        plan = await self._plans.get_or_create(identity.tenant_id, patient_id)
        allergies = await self._patient_allergies(identity, patient_id)
        report = self._safety.check(list(plan.medications), allergies)
        return plan, report

    async def update_medications(
        self,
        identity: AuthenticatedIdentity,
        patient_id: uuid.UUID,
        medications: list[Medication],
        expected_version: int,
        acknowledge_warnings: bool = False,
    ) -> CarePlanUpdateResult:
        """Safety runs BEFORE the write. Flagged updates are not applied
        unless a human explicitly acknowledges the warnings — the agent
        proposes, a human confirms (blueprint safety posture)."""
        if not medications and expected_version == 0:
            raise ValidationError("cannot create an empty plan at version 0")

        allergies = await self._patient_allergies(identity, patient_id)
        report = self._safety.check(medications, allergies)

        if report.has_flags and not acknowledge_warnings:
            current = await self._plans.get_or_create(identity.tenant_id, patient_id)
            await self._audit.record(
                AuditEntry(
                    tenant_id=identity.tenant_id,
                    patient_id=patient_id,
                    actor=str(identity.user_id),
                    action="care_plan.update_blocked_by_safety",
                    detail={
                        "flags": [f.description for f in report.flags],
                        "dataset_version": report.dataset_version,
                    },
                )
            )
            return CarePlanUpdateResult(plan=current, safety=report, applied=False)

        plan = await self._plans.update_medications(
            identity.tenant_id, patient_id, medications, expected_version
        )
        await self._audit.record(
            AuditEntry(
                tenant_id=identity.tenant_id,
                patient_id=patient_id,
                actor=str(identity.user_id),
                action="care_plan.medications_updated",
                detail={
                    "version": plan.version,
                    "medications": [m.name for m in medications],
                    "acknowledged_warnings": acknowledge_warnings and report.has_flags,
                    "flags": [f.description for f in report.flags],
                },
            )
        )
        return CarePlanUpdateResult(plan=plan, safety=report, applied=True)

    async def _patient_allergies(
        self, identity: AuthenticatedIdentity, patient_id: uuid.UUID
    ) -> list[str]:
        patient = await self._patients.get(identity.tenant_id, patient_id)
        return list(patient.allergies) if patient else []

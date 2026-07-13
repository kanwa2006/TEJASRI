"""Patient roster use cases. Every mutation is audited."""

import uuid
from datetime import date

from tejasri.core.errors import NotFoundError
from tejasri.domain.entities import AuditEntry, AuthenticatedIdentity, Patient
from tejasri.domain.interfaces import AuditLog, PatientRepository


class PatientService:
    def __init__(self, patients: PatientRepository, audit: AuditLog) -> None:
        self._patients = patients
        self._audit = audit

    async def create_patient(
        self,
        identity: AuthenticatedIdentity,
        display_name: str,
        external_ref: str | None = None,
        dob: date | None = None,
        conditions: tuple[str, ...] = (),
        allergies: tuple[str, ...] = (),
    ) -> Patient:
        patient = await self._patients.create(
            Patient(
                patient_id=uuid.uuid4(),  # placeholder; DB assigns the real id
                tenant_id=identity.tenant_id,
                display_name=display_name.strip(),
                external_ref=external_ref,
                dob=dob,
                conditions=conditions,
                allergies=allergies,
            )
        )
        await self._audit.record(
            AuditEntry(
                tenant_id=identity.tenant_id,
                patient_id=patient.patient_id,
                actor=str(identity.user_id),
                action="patient.created",
                detail={"display_name": patient.display_name},
            )
        )
        return patient

    async def get_patient(self, identity: AuthenticatedIdentity, patient_id: uuid.UUID) -> Patient:
        patient = await self._patients.get(identity.tenant_id, patient_id)
        if patient is None:
            raise NotFoundError(f"patient not found: {patient_id}")
        return patient

    async def list_patients(self, identity: AuthenticatedIdentity) -> list[Patient]:
        return await self._patients.list_for_tenant(identity.tenant_id)

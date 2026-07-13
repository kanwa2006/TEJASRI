"""Patient roster endpoints (tenant-scoped, authenticated)."""

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from tejasri.api.deps import get_current_identity, get_patient_service
from tejasri.application.patient_service import PatientService
from tejasri.domain.entities import AuthenticatedIdentity, Patient

router = APIRouter(prefix="/patients", tags=["patients"])


class CreatePatientRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=200)
    external_ref: str | None = Field(default=None, max_length=200)
    dob: date | None = None
    conditions: list[str] = Field(default_factory=list, max_length=100)
    allergies: list[str] = Field(default_factory=list, max_length=100)


class PatientResponse(BaseModel):
    patient_id: uuid.UUID
    display_name: str
    external_ref: str | None
    dob: date | None
    conditions: list[str]
    allergies: list[str]

    @classmethod
    def from_entity(cls, patient: Patient) -> "PatientResponse":
        return cls(
            patient_id=patient.patient_id,
            display_name=patient.display_name,
            external_ref=patient.external_ref,
            dob=patient.dob,
            conditions=list(patient.conditions),
            allergies=list(patient.allergies),
        )


@router.post("", response_model=PatientResponse, status_code=201)
async def create_patient(
    body: CreatePatientRequest,
    identity: Annotated[AuthenticatedIdentity, Depends(get_current_identity)],
    patients: Annotated[PatientService, Depends(get_patient_service)],
) -> PatientResponse:
    patient = await patients.create_patient(
        identity=identity,
        display_name=body.display_name,
        external_ref=body.external_ref,
        dob=body.dob,
        conditions=tuple(body.conditions),
        allergies=tuple(body.allergies),
    )
    return PatientResponse.from_entity(patient)


@router.get("", response_model=list[PatientResponse])
async def list_patients(
    identity: Annotated[AuthenticatedIdentity, Depends(get_current_identity)],
    patients: Annotated[PatientService, Depends(get_patient_service)],
) -> list[PatientResponse]:
    return [PatientResponse.from_entity(p) for p in await patients.list_patients(identity)]


@router.get("/{patient_id}", response_model=PatientResponse)
async def get_patient(
    patient_id: uuid.UUID,
    identity: Annotated[AuthenticatedIdentity, Depends(get_current_identity)],
    patients: Annotated[PatientService, Depends(get_patient_service)],
) -> PatientResponse:
    return PatientResponse.from_entity(await patients.get_patient(identity, patient_id))

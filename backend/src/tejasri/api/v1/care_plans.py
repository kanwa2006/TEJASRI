"""Care-plan endpoints: read with live safety verdict, safety-gated updates."""

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from tejasri.api.deps import get_care_plan_service, get_current_identity
from tejasri.application.care_plan_service import CarePlanService
from tejasri.domain.entities import AuthenticatedIdentity, CarePlan
from tejasri.domain.safety import Medication, SafetyReport

router = APIRouter(prefix="/patients/{patient_id}/care-plan", tags=["care-plan"])


class MedicationModel(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    dose: str = Field(default="", max_length=100)
    schedule: str = Field(default="", max_length=200)
    rxnorm: str | None = Field(default=None, max_length=20)

    def to_domain(self) -> Medication:
        return Medication(
            name=self.name, dose=self.dose, schedule=self.schedule, rxnorm=self.rxnorm
        )


class SafetyFlagModel(BaseModel):
    kind: str
    drugs: list[str]
    severity: str | None
    description: str
    source: str
    needs_confirmation: bool


class SafetyReportModel(BaseModel):
    flags: list[SafetyFlagModel]
    checked_pairs: int
    dataset_version: str
    unknown_drugs: list[str]
    max_severity: str | None

    @classmethod
    def from_domain(cls, report: SafetyReport) -> "SafetyReportModel":
        return cls(
            flags=[
                SafetyFlagModel(
                    kind=f.kind.value,
                    drugs=list(f.drugs),
                    severity=f.severity.value if f.severity else None,
                    description=f.description,
                    source=f.source,
                    needs_confirmation=f.needs_confirmation,
                )
                for f in report.flags
            ],
            checked_pairs=report.checked_pairs,
            dataset_version=report.dataset_version,
            unknown_drugs=list(report.unknown_drugs),
            max_severity=report.max_severity.value if report.max_severity else None,
        )


class CarePlanModel(BaseModel):
    care_plan_id: uuid.UUID
    status: str
    medications: list[MedicationModel]
    version: int
    updated_at: datetime

    @classmethod
    def from_domain(cls, plan: CarePlan) -> "CarePlanModel":
        return cls(
            care_plan_id=plan.care_plan_id,
            status=plan.status.value,
            medications=[
                MedicationModel(name=m.name, dose=m.dose, schedule=m.schedule, rxnorm=m.rxnorm)
                for m in plan.medications
            ],
            version=plan.version,
            updated_at=plan.updated_at,
        )


class CarePlanResponse(BaseModel):
    plan: CarePlanModel
    safety: SafetyReportModel


class UpdateMedicationsRequest(BaseModel):
    medications: list[MedicationModel] = Field(max_length=50)
    expected_version: int = Field(ge=1)
    acknowledge_warnings: bool = False


class CarePlanUpdateResponse(BaseModel):
    plan: CarePlanModel
    safety: SafetyReportModel
    applied: bool


@router.get("", response_model=CarePlanResponse)
async def get_care_plan(
    patient_id: uuid.UUID,
    identity: Annotated[AuthenticatedIdentity, Depends(get_current_identity)],
    service: Annotated[CarePlanService, Depends(get_care_plan_service)],
) -> CarePlanResponse:
    plan, safety = await service.get_plan(identity, patient_id)
    return CarePlanResponse(
        plan=CarePlanModel.from_domain(plan), safety=SafetyReportModel.from_domain(safety)
    )


@router.put("/medications", response_model=CarePlanUpdateResponse)
async def update_medications(
    patient_id: uuid.UUID,
    body: UpdateMedicationsRequest,
    identity: Annotated[AuthenticatedIdentity, Depends(get_current_identity)],
    service: Annotated[CarePlanService, Depends(get_care_plan_service)],
) -> CarePlanUpdateResponse:
    """Safety-gated: flagged updates return applied=false with the report
    until a human re-submits with acknowledge_warnings=true."""
    result = await service.update_medications(
        identity,
        patient_id,
        [m.to_domain() for m in body.medications],
        expected_version=body.expected_version,
        acknowledge_warnings=body.acknowledge_warnings,
    )
    return CarePlanUpdateResponse(
        plan=CarePlanModel.from_domain(result.plan),
        safety=SafetyReportModel.from_domain(result.safety),
        applied=result.applied,
    )

"""PatientService behavior: tenant scoping and audit trail."""

import uuid

import pytest

from tejasri.application.patient_service import PatientService
from tejasri.core.errors import NotFoundError
from tejasri.domain.entities import AuthenticatedIdentity, UserRole
from tests.unit.fakes import FakeAuditLog, FakePatientRepository


def identity_for(tenant_id: uuid.UUID) -> AuthenticatedIdentity:
    return AuthenticatedIdentity(
        user_id=uuid.uuid4(), tenant_id=tenant_id, role=UserRole.COORDINATOR
    )


@pytest.fixture
def audit() -> FakeAuditLog:
    return FakeAuditLog()


@pytest.fixture
def service(audit: FakeAuditLog) -> PatientService:
    return PatientService(patients=FakePatientRepository(), audit=audit)


async def test_create_patient_is_audited(service: PatientService, audit: FakeAuditLog) -> None:
    identity = identity_for(uuid.uuid4())
    patient = await service.create_patient(identity, display_name="Asha Rao")
    assert patient.display_name == "Asha Rao"
    assert len(audit.entries) == 1
    entry = audit.entries[0]
    assert entry.action == "patient.created"
    assert entry.patient_id == patient.patient_id
    assert entry.actor == str(identity.user_id)


async def test_patients_are_invisible_across_tenants(service: PatientService) -> None:
    tenant_a, tenant_b = identity_for(uuid.uuid4()), identity_for(uuid.uuid4())
    created = await service.create_patient(tenant_a, display_name="Asha Rao")

    assert await service.list_patients(tenant_b) == []
    with pytest.raises(NotFoundError):
        await service.get_patient(tenant_b, created.patient_id)


async def test_get_missing_patient_raises_not_found(service: PatientService) -> None:
    with pytest.raises(NotFoundError):
        await service.get_patient(identity_for(uuid.uuid4()), uuid.uuid4())

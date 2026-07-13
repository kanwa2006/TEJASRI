"""Row-Level Security: the database itself enforces tenant isolation.

These tests prove the production-readiness claim from the blueprint:
tenant B can never see tenant A's rows, even on a shared connection
pool, and a connection with no tenant context sees nothing at all.
"""

import uuid

import pytest

from tejasri.domain.entities import Patient
from tejasri.infrastructure.db import Database
from tejasri.infrastructure.repositories.accounts import CockroachTenantRepository
from tejasri.infrastructure.repositories.patients import CockroachPatientRepository

pytestmark = pytest.mark.integration


def _patient(tenant_id: uuid.UUID, name: str) -> Patient:
    return Patient(patient_id=uuid.uuid4(), tenant_id=tenant_id, display_name=name)


async def test_tenants_cannot_see_each_others_patients(db: Database) -> None:
    tenants = CockroachTenantRepository(db)
    patients = CockroachPatientRepository(db)

    tenant_a = await tenants.create(f"clinic-a-{uuid.uuid4()}")
    tenant_b = await tenants.create(f"clinic-b-{uuid.uuid4()}")
    created_a = await patients.create(_patient(tenant_a.tenant_id, "Patient A"))
    await patients.create(_patient(tenant_b.tenant_id, "Patient B"))

    names_seen_by_a = {p.display_name for p in await patients.list_for_tenant(tenant_a.tenant_id)}
    assert "Patient A" in names_seen_by_a
    assert "Patient B" not in names_seen_by_a

    # Direct lookup across the boundary is also invisible, not merely filtered.
    assert await patients.get(tenant_b.tenant_id, created_a.patient_id) is None


async def test_connection_without_tenant_context_sees_no_rows(db: Database) -> None:
    tenants = CockroachTenantRepository(db)
    patients = CockroachPatientRepository(db)
    tenant = await tenants.create(f"clinic-{uuid.uuid4()}")
    await patients.create(_patient(tenant.tenant_id, "Invisible Without Context"))

    async with db.system_connection() as conn:
        count = await conn.fetchval("SELECT count(*) FROM patients")
    assert count == 0


async def test_tenant_context_is_cleared_on_connection_release(db: Database) -> None:
    tenants = CockroachTenantRepository(db)
    patients = CockroachPatientRepository(db)
    tenant = await tenants.create(f"clinic-{uuid.uuid4()}")
    await patients.create(_patient(tenant.tenant_id, "Leak Canary"))

    # The pooled connection used above must not leak its tenant context.
    async with db.system_connection() as conn:
        setting = await conn.fetchval("SELECT current_setting('app.tenant_id', true)")
    assert setting in (None, "")

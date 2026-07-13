"""Patient repository and audit log — RLS-scoped, tenant-safe by construction."""

import json
import uuid
from typing import Any

from tejasri.domain.entities import AuditEntry, Patient
from tejasri.infrastructure.db import Database


def _patient_from_row(row: Any) -> Patient:
    return Patient(
        patient_id=row["patient_id"],
        tenant_id=row["tenant_id"],
        display_name=row["display_name"],
        external_ref=row["external_ref"],
        dob=row["dob"],
        conditions=tuple(row["conditions"]),
        allergies=tuple(row["allergies"]),
        created_at=row["created_at"],
    )


class CockroachPatientRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    async def create(self, patient: Patient) -> Patient:
        async with self._db.tenant_connection(patient.tenant_id) as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO patients
                  (tenant_id, external_ref, display_name, dob, conditions, allergies)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING *
                """,
                patient.tenant_id,
                patient.external_ref,
                patient.display_name,
                patient.dob,
                list(patient.conditions),
                list(patient.allergies),
            )
        return _patient_from_row(row)

    async def get(self, tenant_id: uuid.UUID, patient_id: uuid.UUID) -> Patient | None:
        async with self._db.tenant_connection(tenant_id) as conn:
            row = await conn.fetchrow("SELECT * FROM patients WHERE patient_id = $1", patient_id)
        return _patient_from_row(row) if row else None

    async def list_for_tenant(self, tenant_id: uuid.UUID) -> list[Patient]:
        async with self._db.tenant_connection(tenant_id) as conn:
            rows = await conn.fetch("SELECT * FROM patients ORDER BY created_at DESC")
        return [_patient_from_row(r) for r in rows]


class CockroachAuditLog:
    def __init__(self, db: Database) -> None:
        self._db = db

    async def record(self, entry: AuditEntry) -> None:
        async with self._db.tenant_connection(entry.tenant_id) as conn:
            await conn.execute(
                """
                INSERT INTO audit_log (tenant_id, patient_id, actor, action, detail)
                VALUES ($1, $2, $3, $4, $5)
                """,
                entry.tenant_id,
                entry.patient_id,
                entry.actor,
                entry.action,
                json.dumps(entry.detail),
            )

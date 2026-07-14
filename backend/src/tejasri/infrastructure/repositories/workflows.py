"""Care-plan and task repositories — the transactional memory.

Care-plan updates use optimistic versioning inside run_serializable:
concurrent writers either serialize cleanly (retry) or fail loudly with a
version conflict. There is no code path that silently loses a plan edit.
"""

import json
import uuid
from typing import Any

import asyncpg

from tejasri.core.errors import ConflictError, NotFoundError
from tejasri.domain.entities import CarePlan, CarePlanStatus, TaskItem, TaskKind, TaskState
from tejasri.domain.safety import Medication
from tejasri.infrastructure.db import Database


def _medications_from_json(raw: str | list[Any]) -> tuple[Medication, ...]:
    items = json.loads(raw) if isinstance(raw, str) else raw
    return tuple(
        Medication(
            name=item["name"],
            dose=item.get("dose", ""),
            schedule=item.get("schedule", ""),
            rxnorm=item.get("rxnorm"),
        )
        for item in items
    )


def _medications_to_json(medications: list[Medication]) -> str:
    return json.dumps(
        [
            {"name": m.name, "dose": m.dose, "schedule": m.schedule, "rxnorm": m.rxnorm}
            for m in medications
        ]
    )


def _plan_from_row(row: Any) -> CarePlan:
    return CarePlan(
        care_plan_id=row["care_plan_id"],
        tenant_id=row["tenant_id"],
        patient_id=row["patient_id"],
        status=CarePlanStatus(row["status"]),
        medications=_medications_from_json(row["medications"]),
        version=row["version"],
        updated_at=row["updated_at"],
    )


class CockroachCarePlanRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    # NOTE: inside explicit transactions CockroachDB rejects a new statement
    # while another portal is suspended, and asyncpg's fetchrow/fetchval use
    # row-limited portals that stay suspended. Use fetch() (runs the portal
    # to completion) for every statement inside run_serializable.
    async def get_or_create(self, tenant_id: uuid.UUID, patient_id: uuid.UUID) -> CarePlan:
        async def _txn(conn: asyncpg.Connection) -> CarePlan:
            rows = await conn.fetch(
                "SELECT * FROM care_plans WHERE tenant_id = $1 AND patient_id = $2",
                tenant_id,
                patient_id,
            )
            if not rows:
                rows = await conn.fetch(
                    """
                    INSERT INTO care_plans (tenant_id, patient_id)
                    VALUES ($1, $2) RETURNING *
                    """,
                    tenant_id,
                    patient_id,
                )
            return _plan_from_row(rows[0])

        return await self._db.run_serializable(tenant_id, _txn)

    async def update_medications(
        self,
        tenant_id: uuid.UUID,
        patient_id: uuid.UUID,
        medications: list[Medication],
        expected_version: int,
    ) -> CarePlan:
        async def _txn(conn: asyncpg.Connection) -> CarePlan:
            rows = await conn.fetch(
                """
                UPDATE care_plans
                SET medications = $4::JSONB, version = version + 1, updated_at = now()
                WHERE tenant_id = $1 AND patient_id = $2 AND version = $3
                RETURNING *
                """,
                tenant_id,
                patient_id,
                expected_version,
                _medications_to_json(medications),
            )
            if not rows:
                current = await conn.fetch(
                    "SELECT version FROM care_plans WHERE tenant_id = $1 AND patient_id = $2",
                    tenant_id,
                    patient_id,
                )
                if not current:
                    raise NotFoundError(f"no care plan for patient {patient_id}")
                raise ConflictError(
                    f"care plan version conflict: expected {expected_version}, "
                    f"current is {current[0]['version']}"
                )
            return _plan_from_row(rows[0])

        return await self._db.run_serializable(tenant_id, _txn)


def _task_from_row(row: Any) -> TaskItem:
    payload = row["payload"]
    return TaskItem(
        task_id=row["task_id"],
        tenant_id=row["tenant_id"],
        patient_id=row["patient_id"],
        kind=TaskKind(row["kind"]),
        state=TaskState(row["state"]),
        payload=json.loads(payload) if isinstance(payload, str) else payload,
        updated_at=row["updated_at"],
    )


class CockroachTaskRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    async def create(
        self,
        tenant_id: uuid.UUID,
        patient_id: uuid.UUID,
        kind: TaskKind,
        payload: dict[str, object],
    ) -> TaskItem:
        async with self._db.tenant_connection(tenant_id) as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO tasks (tenant_id, patient_id, kind, payload)
                VALUES ($1, $2, $3, $4::JSONB) RETURNING *
                """,
                tenant_id,
                patient_id,
                kind.value,
                json.dumps(payload),
            )
        return _task_from_row(row)

    async def get(self, tenant_id: uuid.UUID, task_id: uuid.UUID) -> TaskItem | None:
        async with self._db.tenant_connection(tenant_id) as conn:
            row = await conn.fetchrow("SELECT * FROM tasks WHERE task_id = $1", task_id)
        return _task_from_row(row) if row else None

    async def list_for_patient(self, tenant_id: uuid.UUID, patient_id: uuid.UUID) -> list[TaskItem]:
        async with self._db.tenant_connection(tenant_id) as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM tasks WHERE tenant_id = $1 AND patient_id = $2
                ORDER BY updated_at DESC
                """,
                tenant_id,
                patient_id,
            )
        return [_task_from_row(r) for r in rows]

    async def set_state(
        self, tenant_id: uuid.UUID, task_id: uuid.UUID, state: TaskState
    ) -> TaskItem:
        async with self._db.tenant_connection(tenant_id) as conn:
            row = await conn.fetchrow(
                """
                UPDATE tasks SET state = $2, updated_at = now()
                WHERE task_id = $1 RETURNING *
                """,
                task_id,
                state.value,
            )
        if row is None:
            raise NotFoundError(f"task not found: {task_id}")
        return _task_from_row(row)

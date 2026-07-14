"""Workflow tasks: a validated state machine, every transition audited."""

import uuid

from tejasri.core.errors import ConflictError, NotFoundError
from tejasri.domain.entities import (
    TASK_TRANSITIONS,
    AuditEntry,
    AuthenticatedIdentity,
    TaskItem,
    TaskKind,
    TaskState,
)
from tejasri.domain.interfaces import AuditLog, TaskRepository


class TaskService:
    def __init__(self, tasks: TaskRepository, audit: AuditLog) -> None:
        self._tasks = tasks
        self._audit = audit

    async def create_task(
        self,
        identity: AuthenticatedIdentity,
        patient_id: uuid.UUID,
        kind: TaskKind,
        payload: dict[str, object] | None = None,
    ) -> TaskItem:
        task = await self._tasks.create(identity.tenant_id, patient_id, kind, payload or {})
        await self._audit.record(
            AuditEntry(
                tenant_id=identity.tenant_id,
                patient_id=patient_id,
                actor=str(identity.user_id),
                action="task.created",
                detail={"task_id": str(task.task_id), "kind": kind.value},
            )
        )
        return task

    async def list_tasks(
        self, identity: AuthenticatedIdentity, patient_id: uuid.UUID
    ) -> list[TaskItem]:
        return await self._tasks.list_for_patient(identity.tenant_id, patient_id)

    async def transition(
        self, identity: AuthenticatedIdentity, task_id: uuid.UUID, to_state: TaskState
    ) -> TaskItem:
        task = await self._tasks.get(identity.tenant_id, task_id)
        if task is None:
            raise NotFoundError(f"task not found: {task_id}")
        if to_state not in TASK_TRANSITIONS[task.state]:
            raise ConflictError(f"illegal task transition {task.state.value} → {to_state.value}")
        updated = await self._tasks.set_state(identity.tenant_id, task_id, to_state)
        await self._audit.record(
            AuditEntry(
                tenant_id=identity.tenant_id,
                patient_id=task.patient_id,
                actor=str(identity.user_id),
                action="task.transitioned",
                detail={
                    "task_id": str(task_id),
                    "from": task.state.value,
                    "to": to_state.value,
                },
            )
        )
        return updated

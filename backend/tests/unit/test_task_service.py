"""TaskService: the workflow state machine rejects illegal transitions."""

import uuid
from datetime import UTC, datetime

import pytest

from tejasri.application.task_service import TaskService
from tejasri.core.errors import ConflictError, NotFoundError
from tejasri.domain.entities import (
    AuthenticatedIdentity,
    TaskItem,
    TaskKind,
    TaskState,
    UserRole,
)
from tests.unit.fakes import FakeAuditLog


class FakeTasks:
    def __init__(self) -> None:
        self.tasks: dict[uuid.UUID, TaskItem] = {}

    async def create(
        self,
        tenant_id: uuid.UUID,
        patient_id: uuid.UUID,
        kind: TaskKind,
        payload: dict[str, object],
    ) -> TaskItem:
        task = TaskItem(
            task_id=uuid.uuid4(),
            tenant_id=tenant_id,
            patient_id=patient_id,
            kind=kind,
            state=TaskState.OPEN,
            payload=payload,
            updated_at=datetime.now(UTC),
        )
        self.tasks[task.task_id] = task
        return task

    async def get(self, tenant_id: uuid.UUID, task_id: uuid.UUID) -> TaskItem | None:
        return self.tasks.get(task_id)

    async def list_for_patient(self, tenant_id: uuid.UUID, patient_id: uuid.UUID) -> list[TaskItem]:
        return [t for t in self.tasks.values() if t.patient_id == patient_id]

    async def set_state(
        self, tenant_id: uuid.UUID, task_id: uuid.UUID, state: TaskState
    ) -> TaskItem:
        old = self.tasks[task_id]
        updated = TaskItem(
            task_id=old.task_id,
            tenant_id=old.tenant_id,
            patient_id=old.patient_id,
            kind=old.kind,
            state=state,
            payload=old.payload,
            updated_at=datetime.now(UTC),
        )
        self.tasks[task_id] = updated
        return updated


@pytest.fixture
def identity() -> AuthenticatedIdentity:
    return AuthenticatedIdentity(
        user_id=uuid.uuid4(), tenant_id=uuid.uuid4(), role=UserRole.COORDINATOR
    )


@pytest.fixture
def audit() -> FakeAuditLog:
    return FakeAuditLog()


@pytest.fixture
def service(audit: FakeAuditLog) -> TaskService:
    return TaskService(tasks=FakeTasks(), audit=audit)


async def test_legal_transition_chain(
    service: TaskService, identity: AuthenticatedIdentity
) -> None:
    task = await service.create_task(identity, uuid.uuid4(), TaskKind.REFILL)
    task = await service.transition(identity, task.task_id, TaskState.IN_PROGRESS)
    task = await service.transition(identity, task.task_id, TaskState.DONE)
    assert task.state is TaskState.DONE


async def test_done_is_terminal(service: TaskService, identity: AuthenticatedIdentity) -> None:
    task = await service.create_task(identity, uuid.uuid4(), TaskKind.FOLLOWUP)
    await service.transition(identity, task.task_id, TaskState.DONE)
    with pytest.raises(ConflictError):
        await service.transition(identity, task.task_id, TaskState.OPEN)


async def test_blocked_can_be_reopened(
    service: TaskService, identity: AuthenticatedIdentity
) -> None:
    task = await service.create_task(identity, uuid.uuid4(), TaskKind.PHARMACIST_REVIEW)
    await service.transition(identity, task.task_id, TaskState.BLOCKED)
    task = await service.transition(identity, task.task_id, TaskState.OPEN)
    assert task.state is TaskState.OPEN


async def test_transitions_are_audited(
    service: TaskService, identity: AuthenticatedIdentity, audit: FakeAuditLog
) -> None:
    task = await service.create_task(identity, uuid.uuid4(), TaskKind.ADHERENCE_CHECK)
    await service.transition(identity, task.task_id, TaskState.DONE)
    actions = [e.action for e in audit.entries]
    assert actions == ["task.created", "task.transitioned"]


async def test_missing_task_raises_not_found(
    service: TaskService, identity: AuthenticatedIdentity
) -> None:
    with pytest.raises(NotFoundError):
        await service.transition(identity, uuid.uuid4(), TaskState.DONE)

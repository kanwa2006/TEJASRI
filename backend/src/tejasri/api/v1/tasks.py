"""Workflow task endpoints: validated state machine over patient tasks."""

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from tejasri.api.deps import get_current_identity, get_task_service
from tejasri.application.task_service import TaskService
from tejasri.domain.entities import AuthenticatedIdentity, TaskItem, TaskKind, TaskState

router = APIRouter(tags=["tasks"])


class TaskModel(BaseModel):
    task_id: uuid.UUID
    patient_id: uuid.UUID
    kind: TaskKind
    state: TaskState
    payload: dict[str, object]
    updated_at: datetime

    @classmethod
    def from_domain(cls, task: TaskItem) -> "TaskModel":
        return cls(
            task_id=task.task_id,
            patient_id=task.patient_id,
            kind=task.kind,
            state=task.state,
            payload=task.payload,
            updated_at=task.updated_at,
        )


class CreateTaskRequest(BaseModel):
    kind: TaskKind
    payload: dict[str, object] = {}


class TransitionRequest(BaseModel):
    to_state: TaskState


@router.post("/patients/{patient_id}/tasks", response_model=TaskModel, status_code=201)
async def create_task(
    patient_id: uuid.UUID,
    body: CreateTaskRequest,
    identity: Annotated[AuthenticatedIdentity, Depends(get_current_identity)],
    service: Annotated[TaskService, Depends(get_task_service)],
) -> TaskModel:
    task = await service.create_task(identity, patient_id, body.kind, body.payload)
    return TaskModel.from_domain(task)


@router.get("/patients/{patient_id}/tasks", response_model=list[TaskModel])
async def list_tasks(
    patient_id: uuid.UUID,
    identity: Annotated[AuthenticatedIdentity, Depends(get_current_identity)],
    service: Annotated[TaskService, Depends(get_task_service)],
) -> list[TaskModel]:
    return [TaskModel.from_domain(t) for t in await service.list_tasks(identity, patient_id)]


@router.post("/tasks/{task_id}/transition", response_model=TaskModel)
async def transition_task(
    task_id: uuid.UUID,
    body: TransitionRequest,
    identity: Annotated[AuthenticatedIdentity, Depends(get_current_identity)],
    service: Annotated[TaskService, Depends(get_task_service)],
) -> TaskModel:
    """Illegal transitions (e.g. done → open) return 409."""
    return TaskModel.from_domain(await service.transition(identity, task_id, body.to_state))

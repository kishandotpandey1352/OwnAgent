from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class WorkflowState(str, Enum):
    pending = "PENDING"
    running = "RUNNING"
    waiting_approval = "WAITING_APPROVAL"
    completed = "COMPLETED"
    partial = "PARTIAL"
    failed = "FAILED"
    cancelled = "CANCELLED"
    dead_letter = "DEAD_LETTER"


_ALLOWED: dict[WorkflowState, set[WorkflowState]] = {
    WorkflowState.pending: {WorkflowState.running, WorkflowState.cancelled},
    WorkflowState.running: {
        WorkflowState.waiting_approval,
        WorkflowState.completed,
        WorkflowState.partial,
        WorkflowState.failed,
        WorkflowState.cancelled,
        WorkflowState.dead_letter,
    },
    WorkflowState.waiting_approval: {
        WorkflowState.running,
        WorkflowState.cancelled,
        WorkflowState.failed,
    },
    WorkflowState.failed: {WorkflowState.running, WorkflowState.dead_letter},
    WorkflowState.partial: set(),
    WorkflowState.completed: set(),
    WorkflowState.cancelled: set(),
    WorkflowState.dead_letter: {WorkflowState.running},
}


class WorkflowRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "WorkflowRecord.v1"
    workflow_id: str
    event_id: str
    tenant_id: str
    state: WorkflowState = WorkflowState.pending
    attempts: int = Field(default=0, ge=0)
    last_error: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class WorkflowStateMachine:
    def transition(self, record: WorkflowRecord, target: WorkflowState) -> WorkflowRecord:
        if target == record.state:
            return record
        allowed = _ALLOWED.get(record.state, set())
        if target not in allowed:
            raise ValueError(f"Invalid workflow transition: {record.state.value} -> {target.value}")
        return record.model_copy(
            update={"state": target, "updated_at": datetime.now(timezone.utc)}
        )

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from app.agents.contracts import AgentResult


class RuntimeModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DAGExecutionStatus(str, Enum):
    completed = "completed"
    partial = "partial"
    failed = "failed"
    timed_out = "timed_out"


class DAGExecutionResult(RuntimeModel):
    schema_version: str = "DAGExecutionResult.v1"
    plan_id: str = Field(min_length=1, max_length=200)
    request_id: str = Field(min_length=1, max_length=200)
    status: DAGExecutionStatus
    results: list[AgentResult] = Field(default_factory=list, max_length=32)
    attempts_by_task: dict[str, int] = Field(default_factory=dict)
    execution_order: list[str] = Field(default_factory=list, max_length=32)
    warnings: list[str] = Field(default_factory=list, max_length=100)
    started_at: datetime
    completed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    latency_ms: int = Field(default=0, ge=0)

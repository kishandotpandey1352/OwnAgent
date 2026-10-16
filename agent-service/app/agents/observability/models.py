from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TraceModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TraceEventType(str, Enum):
    workflow_started = "workflow.started"
    workflow_completed = "workflow.completed"
    workflow_failed = "workflow.failed"
    agent_completed = "agent.completed"
    agent_failed = "agent.failed"
    agent_timed_out = "agent.timed_out"
    agent_skipped = "agent.skipped"


class TraceEvent(TraceModel):
    schema_version: str = "TraceEvent.v1"
    event_type: TraceEventType
    trace_id: str = Field(min_length=1, max_length=200)
    request_id: str = Field(min_length=1, max_length=200)
    plan_id: str | None = Field(default=None, max_length=200)
    task_id: str | None = Field(default=None, max_length=200)
    agent_name: str | None = Field(default=None, max_length=100)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    latency_ms: int | None = Field(default=None, ge=0)
    token_usage: int | None = Field(default=None, ge=0)
    estimated_cost_usd: float | None = Field(default=None, ge=0.0)
    metadata: dict[str, Any] = Field(default_factory=dict, max_length=50)


class TraceSummary(TraceModel):
    schema_version: str = "TraceSummary.v1"
    trace_id: str
    request_id: str
    event_count: int = Field(ge=0)
    agent_count: int = Field(ge=0)
    total_tokens: int = Field(ge=0)
    total_estimated_cost_usd: float = Field(ge=0.0)
    workflow_latency_ms: int = Field(ge=0)

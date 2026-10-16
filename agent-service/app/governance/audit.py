from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


_SECRET_KEY_RE = re.compile(
    r"(authorization|api[_-]?key|access[_-]?token|refresh[_-]?token|password|secret|credential|cookie)",
    re.IGNORECASE,
)
_BEARER_RE = re.compile(r"\bBearer\s+[A-Za-z0-9._~+\-/]+=*", re.IGNORECASE)


class AuditSeverity(str, Enum):
    info = "info"
    warning = "warning"
    error = "error"
    critical = "critical"


class AuditActorType(str, Enum):
    user = "user"
    agent = "agent"
    tool = "tool"
    workflow = "workflow"
    system = "system"


class AuditEvent(BaseModel):
    """Append-only audit record.

    event_hash and previous_event_hash form a tamper-evident chain. The store
    computes both values; callers never provide them as authority.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "AuditEvent.v1"
    event_id: str = Field(default_factory=lambda: f"audit-{uuid4()}")
    request_id: str = Field(min_length=1, max_length=200)
    tenant_id: str | None = Field(default=None, max_length=200)
    user_id: str | None = Field(default=None, max_length=200)
    trace_id: str | None = Field(default=None, max_length=200)
    plan_id: str | None = Field(default=None, max_length=200)
    task_id: str | None = Field(default=None, max_length=200)
    event_type: str = Field(min_length=1, max_length=120)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    actor_type: AuditActorType
    actor_id: str = Field(min_length=1, max_length=200)
    severity: AuditSeverity = AuditSeverity.info
    metadata: dict[str, Any] = Field(default_factory=dict)
    previous_event_hash: str | None = None
    event_hash: str | None = None


def redact_sensitive(value: Any) -> Any:
    """Recursively redact obvious secrets before an object reaches audit storage."""

    if isinstance(value, dict):
        output: dict[str, Any] = {}
        for key, item in value.items():
            if _SECRET_KEY_RE.search(str(key)):
                output[str(key)] = "[REDACTED]"
            else:
                output[str(key)] = redact_sensitive(item)
        return output
    if isinstance(value, list):
        return [redact_sensitive(item) for item in value]
    if isinstance(value, tuple):
        return [redact_sensitive(item) for item in value]
    if isinstance(value, str):
        return _BEARER_RE.sub("Bearer [REDACTED]", value)
    return value


def _canonical_event_payload(event: AuditEvent) -> str:
    payload = event.model_dump(mode="json", exclude={"event_hash"})
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _hash_event(event: AuditEvent) -> str:
    return hashlib.sha256(_canonical_event_payload(event).encode("utf-8")).hexdigest()


class InMemoryAuditStore:
    """Reference append-only store used for tests/local development.

    Production adapters should persist the same AuditEvent contract in an
    append-only database/log sink. No update/delete API is intentionally
    exposed here.
    """

    def __init__(self) -> None:
        self._events: list[AuditEvent] = []

    def append(self, event: AuditEvent) -> AuditEvent:
        previous_hash = self._events[-1].event_hash if self._events else None
        sanitized = event.model_copy(
            update={
                "metadata": redact_sensitive(event.metadata),
                "previous_event_hash": previous_hash,
                "event_hash": None,
            }
        )
        stored = sanitized.model_copy(update={"event_hash": _hash_event(sanitized)})
        self._events.append(stored)
        return stored

    def emit(
        self,
        *,
        request_id: str,
        event_type: str,
        actor_type: AuditActorType,
        actor_id: str,
        tenant_id: str | None = None,
        user_id: str | None = None,
        trace_id: str | None = None,
        plan_id: str | None = None,
        task_id: str | None = None,
        severity: AuditSeverity = AuditSeverity.info,
        metadata: dict[str, Any] | None = None,
    ) -> AuditEvent:
        return self.append(
            AuditEvent(
                request_id=request_id,
                tenant_id=tenant_id,
                user_id=user_id,
                trace_id=trace_id,
                plan_id=plan_id,
                task_id=task_id,
                event_type=event_type,
                actor_type=actor_type,
                actor_id=actor_id,
                severity=severity,
                metadata=metadata or {},
            )
        )

    def list_events(
        self,
        *,
        request_id: str | None = None,
        tenant_id: str | None = None,
    ) -> list[AuditEvent]:
        events = list(self._events)
        if request_id is not None:
            events = [event for event in events if event.request_id == request_id]
        if tenant_id is not None:
            events = [event for event in events if event.tenant_id == tenant_id]
        return events

    def verify_chain(self) -> bool:
        previous_hash: str | None = None
        for event in self._events:
            if event.previous_event_hash != previous_hash:
                return False
            event_without_hash = event.model_copy(update={"event_hash": None})
            if _hash_event(event_without_hash) != event.event_hash:
                return False
            previous_hash = event.event_hash
        return True

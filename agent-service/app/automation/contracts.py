from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AutomationModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class AutomationEventType(str, Enum):
    document_uploaded = "document.uploaded"
    document_indexed = "document.indexed"
    financial_filing_detected = "financial_filing.detected"
    analysis_completed = "analysis.completed"
    compliance_warning = "compliance.warning"
    compliance_failed = "compliance.failed"
    schedule_triggered = "schedule.triggered"
    webhook_received = "webhook.received"


class AutomationEvent(AutomationModel):
    schema_version: str = "AutomationEvent.v1"
    event_id: str = Field(default_factory=lambda: f"evt-{uuid4()}")
    event_type: AutomationEventType
    tenant_id: str = Field(min_length=1, max_length=200)
    user_id: str | None = Field(default=None, max_length=200)
    source: str = Field(min_length=1, max_length=200)
    occurred_at: datetime
    received_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    correlation_id: str = Field(min_length=1, max_length=200)
    idempotency_key: str = Field(min_length=1, max_length=300)
    payload: dict[str, Any] = Field(default_factory=dict)

    @field_validator("occurred_at", "received_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Automation event timestamps must be timezone-aware.")
        return value

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Callable
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.automation.contracts import AutomationEvent


class OutboxStatus(str, Enum):
    pending = "pending"
    published = "published"
    failed = "failed"


class OutboxRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "OutboxRecord.v1"
    outbox_id: str = Field(default_factory=lambda: f"outbox-{uuid4()}")
    event: AutomationEvent
    status: OutboxStatus = OutboxStatus.pending
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    published_at: datetime | None = None
    attempts: int = Field(default=0, ge=0)
    last_error: str | None = None


class InMemoryOutbox:
    """Reference outbox API.

    In production, insert the business row and outbox row in ONE database
    transaction. A background publisher then reads pending rows and publishes
    them to SQS/EventBridge before marking them published.
    """

    def __init__(self) -> None:
        self._records: dict[str, OutboxRecord] = {}

    def add(self, event: AutomationEvent) -> OutboxRecord:
        record = OutboxRecord(event=event)
        self._records[record.outbox_id] = record
        return record

    def pending(self, *, limit: int = 100) -> list[OutboxRecord]:
        return [item for item in self._records.values() if item.status == OutboxStatus.pending][:limit]

    def publish_pending(self, publisher: Callable[[AutomationEvent], None], *, limit: int = 100) -> int:
        count = 0
        for record in self.pending(limit=limit):
            attempts = record.attempts + 1
            try:
                publisher(record.event)
                updated = record.model_copy(
                    update={
                        "status": OutboxStatus.published,
                        "published_at": datetime.now(timezone.utc),
                        "attempts": attempts,
                        "last_error": None,
                    }
                )
                count += 1
            except Exception as exc:
                updated = record.model_copy(
                    update={"attempts": attempts, "last_error": type(exc).__name__}
                )
            self._records[record.outbox_id] = updated
        return count

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.automation.contracts import AutomationEvent


class DeadLetterItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "DeadLetterItem.v1"
    dlq_id: str = Field(default_factory=lambda: f"dlq-{uuid4()}")
    event: AutomationEvent
    workflow_id: str | None = None
    error_category: str
    attempt_count: int = Field(ge=1)
    first_failure_at: datetime
    last_failure_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    trace_id: str | None = None


class DeadLetterStore:
    def __init__(self) -> None:
        self._items: dict[str, DeadLetterItem] = {}

    def add(self, item: DeadLetterItem) -> DeadLetterItem:
        self._items[item.dlq_id] = item
        return item

    def list(self) -> list[DeadLetterItem]:
        return list(self._items.values())

    def get(self, dlq_id: str) -> DeadLetterItem:
        try:
            return self._items[dlq_id]
        except KeyError as exc:
            raise KeyError(f"Unknown DLQ item: {dlq_id}") from exc

    def replay(self, dlq_id: str) -> AutomationEvent:
        item = self.get(dlq_id)
        del self._items[dlq_id]
        return item.event

    def discard(self, dlq_id: str) -> None:
        self.get(dlq_id)
        del self._items[dlq_id]

from __future__ import annotations

import heapq
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.automation.contracts import AutomationEvent
from app.automation.dlq import DeadLetterItem, DeadLetterStore


class QueueMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message_id: str = Field(default_factory=lambda: f"msg-{uuid4()}")
    event: AutomationEvent
    attempt_count: int = Field(default=0, ge=0)
    available_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    first_failure_at: datetime | None = None
    last_error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class InMemoryDurableQueue:
    """Deterministic reference queue with retry/DLQ semantics.

    Production maps this contract to SQS (or the chosen durable queue). The
    in-memory adapter exists so retry/idempotency behavior is fully testable.
    """

    def __init__(self, *, dlq: DeadLetterStore | None = None) -> None:
        self._heap: list[tuple[float, int, QueueMessage]] = []
        self._sequence = 0
        self.dlq = dlq or DeadLetterStore()

    def enqueue(self, event: AutomationEvent, *, delay_seconds: float = 0.0) -> QueueMessage:
        message = QueueMessage(
            event=event,
            available_at=datetime.now(timezone.utc) + timedelta(seconds=max(0.0, delay_seconds)),
        )
        self._put(message)
        return message

    def _put(self, message: QueueMessage) -> None:
        self._sequence += 1
        heapq.heappush(
            self._heap,
            (message.available_at.timestamp(), self._sequence, message),
        )

    def receive(self, *, now: datetime | None = None) -> QueueMessage | None:
        current = now or datetime.now(timezone.utc)
        if not self._heap or self._heap[0][0] > current.timestamp():
            return None
        _, _, message = heapq.heappop(self._heap)
        return message

    def retry_or_dead_letter(
        self,
        message: QueueMessage,
        *,
        error: str,
        max_attempts: int = 3,
        base_delay_seconds: float = 5.0,
        trace_id: str | None = None,
        workflow_id: str | None = None,
    ) -> QueueMessage | DeadLetterItem:
        now = datetime.now(timezone.utc)
        attempt_count = message.attempt_count + 1
        first_failure = message.first_failure_at or now
        if attempt_count >= max_attempts:
            return self.dlq.add(
                DeadLetterItem(
                    event=message.event,
                    workflow_id=workflow_id,
                    error_category=error,
                    attempt_count=attempt_count,
                    first_failure_at=first_failure,
                    last_failure_at=now,
                    trace_id=trace_id,
                )
            )

        delay = base_delay_seconds * (2 ** max(0, attempt_count - 1))
        retried = message.model_copy(
            update={
                "attempt_count": attempt_count,
                "first_failure_at": first_failure,
                "last_error": error,
                "available_at": now + timedelta(seconds=delay),
            }
        )
        self._put(retried)
        return retried

    @property
    def depth(self) -> int:
        return len(self._heap)

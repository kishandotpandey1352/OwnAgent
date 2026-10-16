from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class IdempotencyStatus(str, Enum):
    processing = "processing"
    completed = "completed"
    failed = "failed"


class IdempotencyRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str
    first_seen: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: IdempotencyStatus = IdempotencyStatus.processing
    result: Any = None
    error: str | None = None


class IdempotencyStore:
    """Reference store. Replace with DynamoDB/Aurora conditional writes in production."""

    def __init__(self) -> None:
        self._records: dict[str, IdempotencyRecord] = {}

    def begin(
        self,
        key: str,
        *,
        retry_failed: bool = False,
    ) -> tuple[bool, IdempotencyRecord]:
        existing = self._records.get(key)
        if existing is not None:
            if retry_failed and existing.status == IdempotencyStatus.failed:
                retried = existing.model_copy(
                    update={"status": IdempotencyStatus.processing, "error": None}
                )
                self._records[key] = retried
                return True, retried
            return False, existing
        record = IdempotencyRecord(key=key)
        self._records[key] = record
        return True, record

    def complete(self, key: str, result: Any) -> IdempotencyRecord:
        record = self._require(key).model_copy(
            update={"status": IdempotencyStatus.completed, "result": result, "error": None}
        )
        self._records[key] = record
        return record

    def fail(self, key: str, error: str) -> IdempotencyRecord:
        record = self._require(key).model_copy(
            update={"status": IdempotencyStatus.failed, "error": error}
        )
        self._records[key] = record
        return record

    def get(self, key: str) -> IdempotencyRecord | None:
        return self._records.get(key)

    def _require(self, key: str) -> IdempotencyRecord:
        record = self._records.get(key)
        if record is None:
            raise KeyError(f"Unknown idempotency key: {key}")
        return record

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DailySchedule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schedule_id: str
    timezone: str
    hour: int = Field(ge=0, le=23)
    minute: int = Field(ge=0, le=59)
    enabled: bool = True
    # A local clock time can be nonexistent during spring-forward. Either move
    # to the normalized post-gap time or skip that local date.
    dst_gap_policy: Literal["shift_forward", "skip"] = "shift_forward"

    @model_validator(mode="after")
    def validate_timezone(self) -> "DailySchedule":
        try:
            ZoneInfo(self.timezone)
        except ZoneInfoNotFoundError as exc:
            raise ValueError(f"Unknown IANA timezone: {self.timezone}") from exc
        return self

    def _candidate_for_date(self, local: datetime) -> datetime:
        zone = ZoneInfo(self.timezone)
        naive = datetime(local.year, local.month, local.day, self.hour, self.minute)
        candidate = naive.replace(tzinfo=zone, fold=0)
        # Round-trip detects nonexistent wall times. Ambiguous fall-back times
        # remain valid; fold=0 deliberately chooses the first occurrence.
        normalized = candidate.astimezone(ZoneInfo("UTC")).astimezone(zone)
        if normalized.replace(tzinfo=None) != naive:
            if self.dst_gap_policy == "skip":
                next_day = local + timedelta(days=1)
                return self._candidate_for_date(next_day)
            return normalized
        return candidate

    def next_run(self, after: datetime) -> datetime:
        if after.tzinfo is None or after.utcoffset() is None:
            raise ValueError("after must be timezone-aware")
        zone = ZoneInfo(self.timezone)
        local = after.astimezone(zone)
        candidate = self._candidate_for_date(local)
        if candidate <= local:
            candidate = self._candidate_for_date(local + timedelta(days=1))
        return candidate


class ScheduleLeaseStore:
    """Single-execution lease abstraction for distributed schedulers."""

    def __init__(self) -> None:
        self._leases: set[str] = set()

    def acquire(self, schedule_id: str, scheduled_for: datetime) -> bool:
        key = f"{schedule_id}:{scheduled_for.isoformat()}"
        if key in self._leases:
            return False
        self._leases.add(key)
        return True

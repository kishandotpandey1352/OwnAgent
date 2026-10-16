from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from time import monotonic
from typing import Callable


class CircuitState(str, Enum):
    closed = "closed"
    open = "open"
    half_open = "half_open"


class CircuitBreakerOpen(RuntimeError):
    pass


@dataclass
class CircuitBreaker:
    """Small provider/tool circuit breaker primitive.

    Keep instances at process/service scope (or externalize state) so failures
    across requests contribute to the same dependency health signal.
    """

    failure_threshold: int = 5
    recovery_timeout_seconds: float = 30.0
    clock: Callable[[], float] = monotonic
    state: CircuitState = CircuitState.closed
    consecutive_failures: int = 0
    opened_at: float | None = None

    def before_call(self) -> None:
        if self.state != CircuitState.open:
            return
        assert self.opened_at is not None
        if self.clock() - self.opened_at >= self.recovery_timeout_seconds:
            self.state = CircuitState.half_open
            return
        raise CircuitBreakerOpen("Dependency circuit is open.")

    def record_success(self) -> None:
        self.state = CircuitState.closed
        self.consecutive_failures = 0
        self.opened_at = None

    def record_failure(self) -> None:
        self.consecutive_failures += 1
        if self.state == CircuitState.half_open or self.consecutive_failures >= self.failure_threshold:
            self.state = CircuitState.open
            self.opened_at = self.clock()


class ProviderFallbackPolicy:
    """Ordered list of pre-evaluated provider/model identifiers.

    This object does not decide whether a fallback is safe. The application
    must populate it only with models/providers that passed the same evaluation
    and structured-output requirements for the task class.
    """

    def __init__(self, providers: list[str]) -> None:
        cleaned = [item.strip() for item in providers if item.strip()]
        if not cleaned:
            raise ValueError("At least one evaluated provider is required.")
        if len(cleaned) != len(set(cleaned)):
            raise ValueError("Fallback providers must be unique.")
        self.providers = tuple(cleaned)

    def candidates(self) -> tuple[str, ...]:
        return self.providers

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.governance.metrics import MetricsSnapshot


class SLOTargets(BaseModel):
    model_config = ConfigDict(extra="forbid")

    api_availability: float = Field(default=0.995, ge=0.0, le=1.0)
    multi_agent_p95_latency_ms: float = Field(default=30_000, ge=0.0)
    citation_integrity: float = Field(default=0.99, ge=0.0, le=1.0)
    automation_success_rate: float = Field(default=0.99, ge=0.0, le=1.0)
    max_unhandled_error_rate: float = Field(default=0.005, ge=0.0, le=1.0)
    audit_capture_rate: float = Field(default=0.999, ge=0.0, le=1.0)


class SLOEvaluation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    passed: bool
    violations: list[str]


def evaluate_multi_agent_slos(metrics: MetricsSnapshot, targets: SLOTargets | None = None) -> SLOEvaluation:
    target = targets or SLOTargets()
    violations: list[str] = []
    if metrics.p95_latency_ms > target.multi_agent_p95_latency_ms:
        violations.append("multi_agent_p95_latency")
    if metrics.citation_validity_rate < target.citation_integrity:
        violations.append("citation_integrity")
    return SLOEvaluation(passed=not violations, violations=violations)

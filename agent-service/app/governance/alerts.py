from __future__ import annotations

from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.governance.compliance import ComplianceReport, ComplianceStatus
from app.governance.metrics import MetricsSnapshot


class AlertSeverity(str, Enum):
    info = "info"
    warning = "warning"
    critical = "critical"


class AlertState(str, Enum):
    open = "open"
    acknowledged = "acknowledged"
    resolved = "resolved"


class Alert(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "Alert.v1"
    alert_id: str = Field(default_factory=lambda: f"alert-{uuid4()}")
    code: str
    severity: AlertSeverity
    message: str
    owner: str
    runbook: str
    state: AlertState = AlertState.open


class AlertThresholds(BaseModel):
    model_config = ConfigDict(extra="forbid")

    p95_latency_ms: float = 30_000
    agent_failure_rate: float = 0.05
    citation_validity_rate: float = 0.99
    p95_cost_usd: float = 0.25
    queue_depth: int = 1000
    provider_failure_rate: float = 0.05


def evaluate_alerts(
    metrics: MetricsSnapshot,
    *,
    compliance_reports: list[ComplianceReport] | None = None,
    thresholds: AlertThresholds | None = None,
) -> list[Alert]:
    limits = thresholds or AlertThresholds()
    alerts: list[Alert] = []

    def add(code: str, severity: AlertSeverity, message: str, runbook: str) -> None:
        alerts.append(
            Alert(
                code=code,
                severity=severity,
                message=message,
                owner="ai-platform-oncall",
                runbook=runbook,
            )
        )

    if metrics.p95_latency_ms > limits.p95_latency_ms:
        add("P95_LATENCY_HIGH", AlertSeverity.warning, "p95 workflow latency exceeded target.", "runbooks/latency.md")
    failure_rate = 1.0 - metrics.agent_success_rate
    if failure_rate > limits.agent_failure_rate:
        add("AGENT_FAILURE_RATE_HIGH", AlertSeverity.critical, "Agent failure rate exceeded target.", "runbooks/agent-failure.md")
    if metrics.citation_validity_rate < limits.citation_validity_rate:
        add("CITATION_VALIDITY_LOW", AlertSeverity.critical, "Citation validity fell below target.", "runbooks/citation-integrity.md")
    if metrics.p95_cost_usd > limits.p95_cost_usd:
        add("P95_COST_HIGH", AlertSeverity.warning, "p95 request cost exceeded target.", "runbooks/cost.md")
    if metrics.queue_depth > limits.queue_depth:
        add("QUEUE_BACKLOG_HIGH", AlertSeverity.warning, "Queue backlog exceeded target.", "runbooks/queue-backlog.md")
    if metrics.provider_failure_rate > limits.provider_failure_rate:
        add("PROVIDER_FAILURE_HIGH", AlertSeverity.critical, "Provider failures exceeded target.", "runbooks/provider-failure.md")

    if compliance_reports and any(
        report.status == ComplianceStatus.failed for report in compliance_reports
    ):
        add("COMPLIANCE_FAILURE", AlertSeverity.critical, "One or more compliance evaluations failed.", "runbooks/compliance.md")

    return alerts

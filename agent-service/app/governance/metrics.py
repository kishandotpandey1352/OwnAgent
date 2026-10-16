from __future__ import annotations

from math import ceil
from statistics import mean
from typing import Iterable

from pydantic import BaseModel, ConfigDict, Field

from app.agents.composition.models import ComposedAnswer
from app.agents.contracts import AgentStatus
from app.agents.runtime.models import DAGExecutionResult
from app.governance.compliance import ComplianceReport, ComplianceStatus


class MetricsSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "MetricsSnapshot.v1"
    request_count: int = Field(ge=0)
    grounded_response_rate: float = Field(ge=0.0, le=1.0)
    compliance_pass_rate: float = Field(ge=0.0, le=1.0)
    agent_success_rate: float = Field(ge=0.0, le=1.0)
    agent_timeout_rate: float = Field(ge=0.0, le=1.0)
    average_agent_count: float = Field(ge=0.0)
    average_latency_ms: float = Field(ge=0.0)
    p95_latency_ms: float = Field(ge=0.0)
    average_cost_usd: float = Field(ge=0.0)
    p95_cost_usd: float = Field(ge=0.0)
    citation_validity_rate: float = Field(ge=0.0, le=1.0)
    queue_depth: int = Field(default=0, ge=0)
    provider_failure_rate: float = Field(default=0.0, ge=0.0, le=1.0)


def _p95(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, ceil(0.95 * len(ordered)) - 1)
    return float(ordered[index])


def build_metrics_snapshot(
    *,
    executions: Iterable[DAGExecutionResult],
    answers: Iterable[ComposedAnswer] = (),
    compliance_reports: Iterable[ComplianceReport] = (),
    queue_depth: int = 0,
    provider_failure_count: int = 0,
) -> MetricsSnapshot:
    runs = list(executions)
    answer_list = list(answers)
    reports = list(compliance_reports)

    agent_results = [item for run in runs for item in run.results]
    successful = sum(
        item.status in {AgentStatus.completed, AgentStatus.partial}
        for item in agent_results
    )
    timed_out = sum(item.status == AgentStatus.timed_out for item in agent_results)

    run_costs = [
        sum(item.estimated_cost_usd or 0.0 for item in run.results)
        for run in runs
    ]
    latencies = [float(run.latency_ms) for run in runs]
    citation_checks = [
        check
        for report in reports
        for check in report.checks
        if check.code == "invalid_citation"
    ]

    request_count = len(runs)
    return MetricsSnapshot(
        request_count=request_count,
        grounded_response_rate=(
            sum(answer.grounded for answer in answer_list) / len(answer_list)
            if answer_list
            else 0.0
        ),
        compliance_pass_rate=(
            sum(report.status == ComplianceStatus.passed for report in reports) / len(reports)
            if reports
            else 0.0
        ),
        agent_success_rate=(successful / len(agent_results) if agent_results else 0.0),
        agent_timeout_rate=(timed_out / len(agent_results) if agent_results else 0.0),
        average_agent_count=(
            mean(len(run.results) for run in runs) if runs else 0.0
        ),
        average_latency_ms=(mean(latencies) if latencies else 0.0),
        p95_latency_ms=_p95(latencies),
        average_cost_usd=(mean(run_costs) if run_costs else 0.0),
        p95_cost_usd=_p95(run_costs),
        citation_validity_rate=(
            sum(check.passed for check in citation_checks) / len(citation_checks)
            if citation_checks
            else 1.0
        ),
        queue_depth=queue_depth,
        provider_failure_rate=(
            min(1.0, provider_failure_count / request_count)
            if request_count
            else 0.0
        ),
    )

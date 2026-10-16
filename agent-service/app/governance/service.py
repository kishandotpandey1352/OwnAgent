from __future__ import annotations

from collections import deque

from app.agents.composition.models import ComposedAnswer
from app.agents.runtime.models import DAGExecutionResult
from app.governance.audit import InMemoryAuditStore
from app.governance.compliance import ComplianceReport
from app.governance.metrics import MetricsSnapshot, build_metrics_snapshot


class GovernanceService:
    """Process-local governance facade for local/staging use.

    Production should replace history storage with persistent repositories while
    preserving these contracts. Audit events are already isolated behind the
    append-only store API.
    """

    def __init__(self, *, max_history: int = 1000) -> None:
        self.audit = InMemoryAuditStore()
        self.executions: deque[DAGExecutionResult] = deque(maxlen=max_history)
        self.answers: deque[ComposedAnswer] = deque(maxlen=max_history)
        self.compliance_reports: deque[ComplianceReport] = deque(maxlen=max_history)
        self.queue_depth = 0
        self.provider_failure_count = 0
        self._request_tenants: dict[str, str | None] = {}

    def record(
        self,
        *,
        execution: DAGExecutionResult,
        answer: ComposedAnswer,
        compliance: ComplianceReport,
        tenant_id: str | None = None,
    ) -> None:
        self.executions.append(execution)
        self.answers.append(answer)
        self.compliance_reports.append(compliance)
        self._request_tenants[execution.request_id] = tenant_id

    def compliance_for_tenant(self, tenant_id: str | None = None) -> list[ComplianceReport]:
        reports = list(self.compliance_reports)
        if tenant_id is None:
            return reports
        return [
            report
            for report in reports
            if self._request_tenants.get(report.request_id) == tenant_id
        ]

    def metrics(self, *, tenant_id: str | None = None) -> MetricsSnapshot:
        executions = list(self.executions)
        answers = list(self.answers)
        reports = list(self.compliance_reports)
        if tenant_id is not None:
            executions = [
                item for item in executions
                if self._request_tenants.get(item.request_id) == tenant_id
            ]
            answers = [
                item for item in answers
                if self._request_tenants.get(item.request_id) == tenant_id
            ]
            reports = [
                item for item in reports
                if self._request_tenants.get(item.request_id) == tenant_id
            ]
        return build_metrics_snapshot(
            executions=executions,
            answers=answers,
            compliance_reports=reports,
            queue_depth=self.queue_depth,
            provider_failure_count=self.provider_failure_count,
        )

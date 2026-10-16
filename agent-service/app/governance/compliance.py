from __future__ import annotations

from enum import Enum
from typing import Iterable

from pydantic import BaseModel, ConfigDict, Field

from app.agents.composition.models import ComposedAnswer
from app.agents.contracts import (
    AgentName,
    AgentResult,
    AgentStatus,
    EvidenceReviewStatus,
    EvidenceSourceType,
    ExecutionContext,
)
from app.agents.review.models import EvidenceReviewSummary
from app.agents.security.budgets import BudgetDecision


COMPLIANCE_POLICY_VERSION = "3J-B.1.0.0"


class ComplianceStatus(str, Enum):
    passed = "passed"
    warning = "warning"
    failed = "failed"


class ComplianceCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "ComplianceCheck.v1"
    code: str = Field(min_length=1, max_length=120)
    passed: bool
    risk_points: int = Field(ge=0, le=100)
    message: str = Field(min_length=1, max_length=1000)
    evidence_ids: list[str] = Field(default_factory=list)


class ComplianceReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "ComplianceReport.v1"
    request_id: str
    status: ComplianceStatus
    risk_score: int = Field(ge=0, le=100)
    checks: list[ComplianceCheck] = Field(default_factory=list)

    @property
    def failed_checks(self) -> list[ComplianceCheck]:
        return [check for check in self.checks if not check.passed]


RISK_POINTS = {
    "invalid_citation": 25,
    "unsupported_numeric_claim": 30,
    "period_mismatch": 20,
    "unvalidated_web_fact": 20,
    "high_risk_agent_failure": 10,
    "unauthorized_tool_attempt": 50,
    "execution_budget_exceeded": 10,
}


def _add(
    checks: list[ComplianceCheck],
    *,
    code: str,
    passed: bool,
    message: str,
    evidence_ids: Iterable[str] = (),
) -> None:
    checks.append(
        ComplianceCheck(
            code=code,
            passed=passed,
            risk_points=0 if passed else RISK_POINTS.get(code, 10),
            message=message,
            evidence_ids=sorted(set(evidence_ids)),
        )
    )


def evaluate_compliance(
    *,
    context: ExecutionContext,
    review: EvidenceReviewSummary,
    answer: ComposedAnswer,
    agent_results: Iterable[AgentResult] = (),
    budget_decision: BudgetDecision | None = None,
) -> ComplianceReport:
    """Run deterministic production compliance checks.

    Compliance does not ask an LLM whether the run was safe. All checks are
    based on typed runtime/review/composition contracts.
    """

    if answer.request_id != context.request_id or review.request_id != context.request_id:
        raise ValueError("Compliance inputs must belong to the same request.")

    checks: list[ComplianceCheck] = []
    usable = {
        item.evidence_id: item.reviewed_evidence
        for item in review.reviews
        if item.status in {EvidenceReviewStatus.validated, EvidenceReviewStatus.partial}
    }
    cited = {citation.evidence_id for citation in answer.citations}

    invalid_citations = cited - set(usable)
    _add(
        checks,
        code="invalid_citation",
        passed=not invalid_citations,
        message=(
            "All citations resolve to reviewed usable evidence."
            if not invalid_citations
            else "Citations reference evidence that was not validated/partial: "
            + ", ".join(sorted(invalid_citations))
        ),
        evidence_ids=invalid_citations,
    )

    unsupported_numeric: list[str] = []
    for claim in answer.claims:
        if not claim.numeric_claim:
            continue
        if not claim.evidence_ids or any(eid not in usable for eid in claim.evidence_ids):
            unsupported_numeric.extend(claim.evidence_ids or ["<missing>"])
    _add(
        checks,
        code="unsupported_numeric_claim",
        passed=not unsupported_numeric,
        message=(
            "All numeric claims are linked to reviewed evidence."
            if not unsupported_numeric
            else "At least one numeric claim lacks reviewed evidence."
        ),
        evidence_ids=unsupported_numeric,
    )

    period_issues = [
        item.evidence_id
        for item in usable.values()
        if item.metric
        and item.normalized_numeric_value is not None
        and not item.period_label
        and item.period_start is None
        and item.period_end is None
    ]
    _add(
        checks,
        code="period_mismatch",
        passed=not period_issues,
        message=(
            "Numeric financial evidence has period context."
            if not period_issues
            else "Numeric evidence is missing period context."
        ),
        evidence_ids=period_issues,
    )

    web_issues = [
        item.evidence_id
        for item in usable.values()
        if item.source.source_type == EvidenceSourceType.web
        and (
            not context.allow_web_fallback
            or item.review_status not in {EvidenceReviewStatus.validated, EvidenceReviewStatus.partial}
        )
    ]
    _add(
        checks,
        code="unvalidated_web_fact",
        passed=not web_issues,
        message=(
            "Web evidence use complies with execution policy."
            if not web_issues
            else "Web evidence was used outside the permitted/reviewed boundary."
        ),
        evidence_ids=web_issues,
    )

    results = list(agent_results)
    high_risk_failures = [
        result.task_id
        for result in results
        if result.status in {AgentStatus.failed, AgentStatus.timed_out}
        and result.agent_name in {
            AgentName.financial_fact_agent,
            AgentName.calculation_agent,
            AgentName.evidence_review_agent,
        }
    ]
    _add(
        checks,
        code="high_risk_agent_failure",
        passed=not high_risk_failures,
        message=(
            "No high-risk specialist failure was recorded."
            if not high_risk_failures
            else "A financial/review specialist failed or timed out."
        ),
    )

    unauthorized = [
        result.task_id
        for result in results
        if result.error
        and result.error.code.upper() in {
            "UNAUTHORIZED_TOOL",
            "UNAUTHORIZED_EXECUTION",
            "TOOL_NOT_ALLOWED",
            "AGENT_NOT_ALLOWED",
        }
    ]
    _add(
        checks,
        code="unauthorized_tool_attempt",
        passed=not unauthorized,
        message=(
            "No unauthorized agent/tool attempt was recorded."
            if not unauthorized
            else "Unauthorized agent/tool activity was blocked."
        ),
    )

    budget_violations = (
        list(budget_decision.violations)
        if budget_decision is not None and not budget_decision.allowed
        else []
    )
    _add(
        checks,
        code="execution_budget_exceeded",
        passed=not budget_violations,
        message=(
            "Execution remained within configured runtime budgets."
            if not budget_violations
            else "Execution exceeded configured budget: "
            + "; ".join(budget_violations)
        ),
    )

    risk_score = min(100, sum(check.risk_points for check in checks if not check.passed))
    if risk_score >= 50:
        status = ComplianceStatus.failed
    elif risk_score > 0 or not answer.grounded or review.overall_status != EvidenceReviewStatus.validated:
        status = ComplianceStatus.warning
    else:
        status = ComplianceStatus.passed

    return ComplianceReport(
        request_id=context.request_id,
        status=status,
        risk_score=risk_score,
        checks=checks,
    )

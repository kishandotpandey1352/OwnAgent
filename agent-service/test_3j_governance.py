from datetime import datetime, timezone
from decimal import Decimal

from app.agents.composition import AnswerComposer
from app.agents.contracts import (
    AgentEvidence,
    AgentName,
    AgentRequest,
    AgentResult,
    AgentStatus,
    EvidenceSource,
    EvidenceSourceType,
    ExecutionContext,
    ExecutionLimits,
)
from app.agents.review import EvidenceReviewer
from app.agents.runtime.models import DAGExecutionResult, DAGExecutionStatus
from app.agents.security.budgets import BudgetDecision, BudgetUsage
from app.versioning import build_execution_version_manifest

from app.governance import (
    AuditActorType,
    AuditPrincipal,
    AuditRole,
    InMemoryAuditStore,
    build_metrics_snapshot,
    evaluate_alerts,
    evaluate_compliance,
    filter_visible_events,
)

limits = ExecutionLimits(
    max_agent_count=6,
    max_coordinator_rounds=2,
    max_retries_per_agent=1,
    max_graph_depth=4,
    max_web_searches=2,
    max_web_fetches=8,
    request_timeout_seconds=90,
    max_concurrency=3,
    max_llm_tokens=20000,
    max_estimated_cost_usd=1.0,
)
context = ExecutionContext(
    request_id="req-gov",
    user_id="u1",
    tenant_id="t1",
    trace_id="tr1",
    limits=limits,
)
request = AgentRequest(
    request_id="req-gov",
    question="What was revenue?",
    user_id="u1",
    tenant_id="t1",
)
evidence = AgentEvidence(
    evidence_id="ev-gov",
    source_agent=AgentName.financial_fact_agent,
    source=EvidenceSource(
        source_type=EvidenceSourceType.document,
        source_id="src",
        document_id="doc-1",
        page_number=1,
    ),
    entity="A",
    metric="Revenue",
    raw_value="100",
    normalized_numeric_value=Decimal("100"),
    currency="USD",
    scale="unit",
    period_label="FY2025",
    snippet="Revenue 100",
)
agent_result = AgentResult(
    task_id="fact",
    request_id="req-gov",
    agent_name=AgentName.financial_fact_agent,
    status=AgentStatus.completed,
    evidence=[evidence],
    latency_ms=50,
    token_usage=100,
    estimated_cost_usd=0.002,
)
review = EvidenceReviewer().review(request_id="req-gov", agent_results=[agent_result])
answer = AnswerComposer().compose(request=request, review=review)
report = evaluate_compliance(
    context=context,
    review=review,
    answer=answer,
    agent_results=[agent_result],
)
assert report.status.value == "passed"
assert report.risk_score == 0

over_budget = BudgetDecision(
    allowed=False,
    violations=["max_llm_tokens exceeded"],
    usage=BudgetUsage(
        agent_count=1,
        retry_count=0,
        llm_tokens=25000,
        estimated_cost_usd=0.02,
        wall_clock_ms=75,
    ),
)
budget_report = evaluate_compliance(
    context=context,
    review=review,
    answer=answer,
    agent_results=[agent_result],
    budget_decision=over_budget,
)
assert any(check.code == "execution_budget_exceeded" and not check.passed for check in budget_report.checks)

manifest = build_execution_version_manifest(
    coordinator_version="3I-C.test",
    workflow_version="3I-H.test",
    reviewer_version="3I-E.test",
    composer_version="3I-F.test",
    provider_id="openai-premium",
    model="test-model",
)
assert manifest.database_schema_version == "phase3_001"
assert manifest.provider_id == "openai-premium"
assert manifest.model == "test-model"

now = datetime.now(timezone.utc)
execution = DAGExecutionResult(
    plan_id="p1",
    request_id="req-gov",
    status=DAGExecutionStatus.completed,
    results=[agent_result],
    attempts_by_task={"fact": 1},
    execution_order=["fact"],
    started_at=now,
    completed_at=now,
    latency_ms=75,
)
metrics = build_metrics_snapshot(
    executions=[execution],
    answers=[answer],
    compliance_reports=[report],
)
assert metrics.grounded_response_rate == 1.0
assert metrics.citation_validity_rate == 1.0
assert evaluate_alerts(metrics, compliance_reports=[report]) == []

store = InMemoryAuditStore()
e1 = store.emit(
    request_id="req-gov",
    tenant_id="t1",
    user_id="u1",
    event_type="request.received",
    actor_type=AuditActorType.user,
    actor_id="u1",
    metadata={"authorization": "Bearer top-secret", "ok": True},
)
e2 = store.emit(
    request_id="req-gov",
    tenant_id="t1",
    user_id="u1",
    event_type="compliance.completed",
    actor_type=AuditActorType.system,
    actor_id="3j",
    metadata={"risk": 0},
)
assert e1.metadata["authorization"] == "[REDACTED]"
assert e2.previous_event_hash == e1.event_hash
assert store.verify_chain() is True

u1 = AuditPrincipal(user_id="u1", tenant_id="t1", role=AuditRole.user)
u2 = AuditPrincipal(user_id="u2", tenant_id="t1", role=AuditRole.user)
auditor = AuditPrincipal(user_id="audit", tenant_id="t1", role=AuditRole.auditor)
assert len(filter_visible_events(u1, store.list_events())) == 2
assert len(filter_visible_events(u2, store.list_events())) == 0
assert len(filter_visible_events(auditor, store.list_events())) == 2

print("PASS: 3J audit, compliance, metrics, RBAC and alert foundations validated.")

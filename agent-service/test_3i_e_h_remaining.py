from datetime import datetime, timezone
from decimal import Decimal

from app.agents.composition import AnswerComposer
from app.agents.contracts import (
    AgentEvidence,
    AgentName,
    AgentRequest,
    AgentResult,
    AgentStatus,
    AgentTask,
    CoordinatorPlan,
    EvidenceSource,
    EvidenceSourceType,
    ExecutionContext,
    ExecutionLimits,
)
from app.agents.observability import events_from_execution, summarize_trace
from app.agents.review import EvidenceReviewer
from app.agents.runtime.models import DAGExecutionResult, DAGExecutionStatus
from app.agents.security import evaluate_budget, validate_request_context


def limits() -> ExecutionLimits:
    return ExecutionLimits(
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


request = AgentRequest(
    request_id="req-1",
    question="What was revenue in FY2025?",
    user_id="user-1",
    tenant_id="tenant-1",
    use_documents=True,
    document_ids=["doc-1"],
)
context = ExecutionContext(
    request_id="req-1",
    user_id="user-1",
    tenant_id="tenant-1",
    trace_id="trace-1",
    use_documents=True,
    document_ids=["doc-1"],
    limits=limits(),
)

evidence = AgentEvidence(
    evidence_id="ev-1",
    source_agent=AgentName.financial_fact_agent,
    source=EvidenceSource(
        source_type=EvidenceSourceType.document,
        source_id="source-1",
        document_id="doc-1",
        page_number=4,
    ),
    entity="Example Plc",
    metric="Revenue",
    raw_value="Revenue was GBP 12.8 million",
    normalized_numeric_value=Decimal("12800000"),
    currency="GBP",
    scale="unit",
    period_label="FY2025",
    confidence=0.98,
    snippet="Revenue was GBP 12.8 million.",
)
result = AgentResult(
    task_id="fact",
    request_id="req-1",
    agent_name=AgentName.financial_fact_agent,
    status=AgentStatus.completed,
    evidence=[evidence],
    latency_ms=100,
    token_usage=250,
    estimated_cost_usd=0.01,
)

review = EvidenceReviewer().review(request_id="req-1", agent_results=[result])
assert review.overall_status.value == "validated"
assert review.validated_evidence_ids == ["ev-1"]

answer = AnswerComposer().compose(request=request, review=review)
assert answer.grounded is True
assert answer.citations[0].evidence_id == "ev-1"
assert answer.claims[0].evidence_ids == ["ev-1"]

plan = CoordinatorPlan(
    plan_id="plan-1",
    request_id="req-1",
    tasks=[
        AgentTask(
            task_id="fact",
            request_id="req-1",
            agent_name=AgentName.financial_fact_agent,
            instruction="extract revenue",
            timeout_seconds=10,
            retry_limit=1,
            estimated_cost_limit_usd=0.1,
        )
    ],
    coordinator_version="test",
    estimated_cost_limit_usd=0.1,
)

security = validate_request_context(request=request, context=context)
assert security.allowed is True
pre_budget = evaluate_budget(context=context, plan=plan)
assert pre_budget.allowed is True

now = datetime.now(timezone.utc)
execution = DAGExecutionResult(
    plan_id="plan-1",
    request_id="req-1",
    status=DAGExecutionStatus.completed,
    results=[result],
    attempts_by_task={"fact": 1},
    execution_order=["fact"],
    started_at=now,
    completed_at=now,
    latency_ms=110,
)
post_budget = evaluate_budget(context=context, plan=plan, result=execution)
assert post_budget.allowed is True

events = events_from_execution(context=context, result=execution)
summary = summarize_trace(events)
assert summary.trace_id == "trace-1"
assert summary.agent_count == 1
assert summary.total_tokens == 250

print("PASS: 3I-E through 3I-H review, composition, security/budget and tracing validated.")

unsafe = AnswerComposer(renderer=lambda payload: "Invented unsupported number: 999")
unsafe_answer = unsafe.compose(request=request, review=review)
assert unsafe_answer.renderer == "deterministic"
assert any("no grounding validator" in warning for warning in unsafe_answer.warnings)

validated_renderer = AnswerComposer(
    renderer=lambda payload: payload["claims"][0]["text"],
    validator=lambda text, claims: text == claims[0].text,
)
validated_answer = validated_renderer.compose(request=request, review=review)
assert validated_answer.renderer != "deterministic"
assert validated_answer.grounded is True

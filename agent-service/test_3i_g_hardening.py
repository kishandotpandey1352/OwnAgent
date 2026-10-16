from datetime import datetime, timezone

from app.agents.contracts import (
    AgentName,
    AgentRequest,
    AgentTask,
    CoordinatorPlan,
    ExecutionContext,
    ExecutionLimits,
)
from app.agents.reliability import CircuitBreaker, CircuitBreakerOpen, CircuitState, ProviderFallbackPolicy
from app.agents.security import evaluate_budget, validate_request_context

limits = ExecutionLimits(
    max_agent_count=2,
    max_coordinator_rounds=1,
    max_retries_per_agent=1,
    max_graph_depth=2,
    max_web_searches=0,
    max_web_fetches=0,
    request_timeout_seconds=5,
    max_concurrency=1,
    max_llm_tokens=10,
    max_estimated_cost_usd=0.05,
)
context = ExecutionContext(
    request_id="r1",
    user_id="u1",
    tenant_id="t1",
    document_ids=["d1"],
    limits=limits,
)
escalation = AgentRequest(
    request_id="r1",
    question="x",
    user_id="u2",
    tenant_id="t1",
    use_documents=True,
    document_ids=["d1", "d2"],
    allow_web_fallback=True,
)
decision = validate_request_context(request=escalation, context=context)
assert decision.allowed is False
assert "user_id mismatch" in decision.violations
assert "document scope escalation" in decision.violations
assert "web permission escalation" in decision.violations

task = AgentTask(
    task_id="t1",
    request_id="r1",
    agent_name=AgentName.document_agent,
    instruction="search",
    timeout_seconds=1,
    retry_limit=0,
    estimated_cost_limit_usd=0.1,
)
plan = CoordinatorPlan(
    plan_id="p1",
    request_id="r1",
    tasks=[task],
    coordinator_version="test",
    estimated_cost_limit_usd=0.1,
)
budget = evaluate_budget(context=context, plan=plan)
assert budget.allowed is False
assert "max_estimated_cost_usd exceeded" in budget.violations

clock = [0.0]
breaker = CircuitBreaker(failure_threshold=2, recovery_timeout_seconds=10, clock=lambda: clock[0])
breaker.record_failure()
assert breaker.state == CircuitState.closed
breaker.record_failure()
assert breaker.state == CircuitState.open
try:
    breaker.before_call()
except CircuitBreakerOpen:
    pass
else:
    raise AssertionError("Open circuit must block calls")
clock[0] = 11.0
breaker.before_call()
assert breaker.state == CircuitState.half_open
breaker.record_success()
assert breaker.state == CircuitState.closed

fallback = ProviderFallbackPolicy(["primary-evaluated-model", "fallback-evaluated-model"])
assert fallback.candidates()[1] == "fallback-evaluated-model"

print("PASS: 3I-G abuse budgets, scope escalation, circuit breaker and evaluated fallback policy validated.")

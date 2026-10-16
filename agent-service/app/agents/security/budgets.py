from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.agents.contracts import CoordinatorPlan, ExecutionContext
from app.agents.runtime.models import DAGExecutionResult


class BudgetModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BudgetUsage(BudgetModel):
    schema_version: str = "BudgetUsage.v1"
    agent_count: int = Field(ge=0)
    retry_count: int = Field(ge=0)
    llm_tokens: int = Field(ge=0)
    estimated_cost_usd: float = Field(ge=0.0)
    wall_clock_ms: int = Field(ge=0)
    coordinator_rounds: int = Field(default=1, ge=0)
    web_searches: int = Field(default=0, ge=0)
    web_fetches: int = Field(default=0, ge=0)


class BudgetDecision(BudgetModel):
    schema_version: str = "BudgetDecision.v1"
    allowed: bool
    violations: list[str] = Field(default_factory=list, max_length=20)
    usage: BudgetUsage


def measure_usage(result: DAGExecutionResult) -> BudgetUsage:
    return BudgetUsage(
        agent_count=len(result.results),
        retry_count=sum(max(0, count - 1) for count in result.attempts_by_task.values()),
        llm_tokens=sum(item.token_usage or 0 for item in result.results),
        estimated_cost_usd=sum(item.estimated_cost_usd or 0.0 for item in result.results),
        wall_clock_ms=result.latency_ms,
        coordinator_rounds=1,
        web_searches=sum(int(item.metadata.get("web_search_count", 0) or 0) for item in result.results),
        web_fetches=sum(int(item.metadata.get("web_fetch_count", 0) or 0) for item in result.results),
    )


def evaluate_budget(
    *,
    context: ExecutionContext,
    plan: CoordinatorPlan,
    result: DAGExecutionResult | None = None,
) -> BudgetDecision:
    if result is None:
        usage = BudgetUsage(
            agent_count=len(plan.tasks),
            retry_count=0,
            llm_tokens=0,
            estimated_cost_usd=plan.estimated_cost_limit_usd,
            wall_clock_ms=0,
            coordinator_rounds=int(plan.metadata.get("coordinator_rounds", 1) or 1),
            web_searches=sum(task.agent_name.value == "web_research_agent" for task in plan.tasks),
            web_fetches=0,
        )
    else:
        usage = measure_usage(result)

    limits = context.limits
    violations: list[str] = []
    if usage.agent_count > limits.max_agent_count:
        violations.append("max_agent_count exceeded")
    if usage.llm_tokens > limits.max_llm_tokens:
        violations.append("max_llm_tokens exceeded")
    if usage.estimated_cost_usd > limits.max_estimated_cost_usd:
        violations.append("max_estimated_cost_usd exceeded")
    if usage.wall_clock_ms > int(limits.request_timeout_seconds * 1000):
        violations.append("request_timeout_seconds exceeded")
    if usage.coordinator_rounds > limits.max_coordinator_rounds:
        violations.append("max_coordinator_rounds exceeded")
    if usage.web_searches > limits.max_web_searches:
        violations.append("max_web_searches exceeded")
    if usage.web_fetches > limits.max_web_fetches:
        violations.append("max_web_fetches exceeded")

    return BudgetDecision(
        allowed=not violations,
        violations=violations,
        usage=usage,
    )

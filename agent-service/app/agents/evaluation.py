from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.agents.contracts import AgentName, CoordinatorPlan
from app.agents.runtime.models import DAGExecutionResult


class EvaluationCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    category: str
    question: str
    expected_agents: list[AgentName] = Field(default_factory=list)
    forbidden_agents: list[AgentName] = Field(default_factory=list)
    expected_runtime_status: str | None = None


class EvaluationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    passed: bool
    routing_precision: float = Field(ge=0.0, le=1.0)
    routing_recall: float = Field(ge=0.0, le=1.0)
    violations: list[str] = Field(default_factory=list)


def evaluate_routing(
    case: EvaluationCase,
    *,
    plan: CoordinatorPlan,
    execution: DAGExecutionResult | None = None,
) -> EvaluationResult:
    actual = {task.agent_name for task in plan.tasks}
    expected = set(case.expected_agents)
    forbidden = set(case.forbidden_agents)
    true_positive = len(actual & expected)
    precision = true_positive / len(actual) if actual else (1.0 if not expected else 0.0)
    recall = true_positive / len(expected) if expected else (1.0 if not actual else 0.0)
    violations: list[str] = []
    missing = expected - actual
    unexpected_forbidden = forbidden & actual
    if missing:
        violations.append("missing expected agents: " + ", ".join(sorted(item.value for item in missing)))
    if unexpected_forbidden:
        violations.append("forbidden agents selected: " + ", ".join(sorted(item.value for item in unexpected_forbidden)))
    if case.expected_runtime_status and execution is not None:
        if execution.status.value != case.expected_runtime_status:
            violations.append(
                f"runtime status {execution.status.value!r} != {case.expected_runtime_status!r}"
            )
    return EvaluationResult(
        case_id=case.case_id,
        passed=not violations,
        routing_precision=precision,
        routing_recall=recall,
        violations=violations,
    )

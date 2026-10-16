from __future__ import annotations

from copy import deepcopy

from app.agents.contracts import (
    AgentName,
    AgentRequest,
    AgentTask,
    CoordinatorPlan,
    ExecutionContext,
    ExecutionLimits,
)
from app.agents.coordinator import (
    CoordinatorPlanValidationError,
    build_coordinator_plan,
    validate_coordinator_plan,
)
from app.agents.registry import get_agent_definition


def limits(**overrides) -> ExecutionLimits:
    payload = dict(
        max_agent_count=6,
        max_coordinator_rounds=2,
        max_retries_per_agent=1,
        max_graph_depth=4,
        max_web_searches=2,
        max_web_fetches=8,
        request_timeout_seconds=90,
        max_concurrency=3,
        max_llm_tokens=24000,
        max_estimated_cost_usd=0.50,
    )
    payload.update(overrides)
    return ExecutionLimits(**payload)


def context(
    *,
    use_documents: bool = False,
    allow_web: bool = False,
    dataset_id: str | None = None,
    execution_limits: ExecutionLimits | None = None,
) -> ExecutionContext:
    return ExecutionContext(
        request_id="req-3ic",
        user_id="local-demo-user",
        use_documents=use_documents,
        document_ids=["doc-1"] if use_documents else [],
        top_k=6,
        dataset_id=dataset_id,
        allow_web_fallback=allow_web,
        trusted_web_domains=["sec.gov"] if allow_web else [],
        limits=execution_limits or limits(),
    )


def request(
    question: str,
    *,
    use_documents: bool = False,
    allow_web: bool = False,
    dataset_id: str | None = None,
    metadata: dict | None = None,
) -> AgentRequest:
    return AgentRequest(
        request_id="req-3ic",
        user_id="local-demo-user",
        question=question,
        use_documents=use_documents,
        document_ids=["doc-1"] if use_documents else [],
        top_k=6,
        dataset_id=dataset_id,
        allow_web_fallback=allow_web,
        trusted_web_domains=["sec.gov"] if allow_web else [],
        metadata=metadata or {},
    )


def names(plan: CoordinatorPlan) -> list[AgentName]:
    return [task.agent_name for task in plan.tasks]


def test_simple_document_question_routes_minimally() -> None:
    plan = build_coordinator_plan(
        request("Summarize the risks in this report.", use_documents=True),
        context(use_documents=True),
    )
    assert names(plan) == [AgentName.document_agent]


def test_financial_document_question_adds_fact_agent() -> None:
    plan = build_coordinator_plan(
        request("What was commission income in 2024?", use_documents=True),
        context(use_documents=True),
    )
    assert names(plan) == [
        AgentName.document_agent,
        AgentName.financial_fact_agent,
    ]
    fact_task = plan.tasks[1]
    assert fact_task.dependencies == ["task-document_agent"]


def test_latest_financial_comparison_can_use_web_only_when_allowed() -> None:
    plan = build_coordinator_plan(
        request(
            "Compare 2024 commission income with the latest value and calculate growth.",
            use_documents=True,
            allow_web=True,
        ),
        context(use_documents=True, allow_web=True),
    )
    assert names(plan) == [
        AgentName.document_agent,
        AgentName.financial_fact_agent,
        AgentName.web_research_agent,
        AgentName.calculation_agent,
    ]
    calc_task = plan.tasks[-1]
    assert "task-financial_fact_agent" in calc_task.dependencies
    assert "task-web_research_agent" in calc_task.dependencies


def test_web_agent_is_not_scheduled_without_permission() -> None:
    plan = build_coordinator_plan(
        request(
            "Compare 2024 commission income with the latest value.",
            use_documents=True,
            allow_web=False,
        ),
        context(use_documents=True, allow_web=False),
    )
    assert AgentName.web_research_agent not in names(plan)


def test_dataset_routes_to_data_agent() -> None:
    plan = build_coordinator_plan(
        request("Analyze this dataset.", dataset_id="dataset-1"),
        context(dataset_id="dataset-1"),
    )
    assert names(plan) == [AgentName.data_analysis_agent]


def test_dataset_chart_adds_chart_dependency() -> None:
    plan = build_coordinator_plan(
        request("Plot revenue by month.", dataset_id="dataset-1"),
        context(dataset_id="dataset-1"),
    )
    assert names(plan) == [
        AgentName.data_analysis_agent,
        AgentName.chart_agent,
    ]
    assert plan.tasks[-1].dependencies == ["task-data_analysis_agent"]


def test_direct_numeric_calculation_routes_only_calculator() -> None:
    plan = build_coordinator_plan(
        request("Calculate growth from 100 to 110."),
        context(),
    )
    assert names(plan) == [AgentName.calculation_agent]


def _registered_task(
    agent_name: AgentName,
    *,
    task_id: str,
    dependencies: list[str] | None = None,
) -> AgentTask:
    definition = get_agent_definition(agent_name)
    return AgentTask(
        task_id=task_id,
        request_id="req-3ic",
        agent_name=agent_name,
        instruction="test",
        dependencies=dependencies or [],
        required=True,
        timeout_seconds=definition.timeout_seconds,
        retry_limit=definition.retry_limit,
        estimated_cost_limit_usd=definition.estimated_cost_limit_usd,
    )


def test_validator_rejects_cycles() -> None:
    tasks = [
        _registered_task(
            AgentName.document_agent,
            task_id="a",
            dependencies=["b"],
        ),
        _registered_task(
            AgentName.financial_fact_agent,
            task_id="b",
            dependencies=["a"],
        ),
    ]
    total = sum(task.estimated_cost_limit_usd for task in tasks)
    plan = CoordinatorPlan(
        plan_id="plan-cycle",
        request_id="req-3ic",
        tasks=tasks,
        coordinator_version="test",
        estimated_cost_limit_usd=total,
    )
    try:
        validate_coordinator_plan(plan, context(use_documents=True))
    except CoordinatorPlanValidationError:
        pass
    else:
        raise AssertionError("Expected dependency cycle to be rejected.")


def test_validator_rejects_web_without_permission() -> None:
    task = _registered_task(
        AgentName.web_research_agent,
        task_id="web",
    )
    plan = CoordinatorPlan(
        plan_id="plan-web",
        request_id="req-3ic",
        tasks=[task],
        coordinator_version="test",
        estimated_cost_limit_usd=task.estimated_cost_limit_usd,
    )
    try:
        validate_coordinator_plan(plan, context(allow_web=False))
    except CoordinatorPlanValidationError:
        pass
    else:
        raise AssertionError("Expected unauthorized web plan to be rejected.")


def test_validator_rejects_task_count_limit() -> None:
    plan = build_coordinator_plan(
        request(
            "Compare 2024 revenue with the latest value and calculate growth.",
            use_documents=True,
            allow_web=True,
        ),
        context(use_documents=True, allow_web=True),
    )
    restricted = context(
        use_documents=True,
        allow_web=True,
        execution_limits=limits(max_agent_count=2),
    )
    try:
        validate_coordinator_plan(plan, restricted)
    except CoordinatorPlanValidationError:
        pass
    else:
        raise AssertionError("Expected max_agent_count violation to be rejected.")


def test_validator_rejects_cost_budget() -> None:
    task = _registered_task(
        AgentName.web_research_agent,
        task_id="web",
    )
    plan = CoordinatorPlan(
        plan_id="plan-cost",
        request_id="req-3ic",
        tasks=[task],
        coordinator_version="test",
        estimated_cost_limit_usd=task.estimated_cost_limit_usd,
    )
    restricted = context(
        allow_web=True,
        execution_limits=limits(max_estimated_cost_usd=0.01),
    )
    try:
        validate_coordinator_plan(plan, restricted)
    except CoordinatorPlanValidationError:
        pass
    else:
        raise AssertionError("Expected request cost budget violation to be rejected.")


def main() -> None:
    test_simple_document_question_routes_minimally()
    test_financial_document_question_adds_fact_agent()
    test_latest_financial_comparison_can_use_web_only_when_allowed()
    test_web_agent_is_not_scheduled_without_permission()
    test_dataset_routes_to_data_agent()
    test_dataset_chart_adds_chart_dependency()
    test_direct_numeric_calculation_routes_only_calculator()
    test_validator_rejects_cycles()
    test_validator_rejects_web_without_permission()
    test_validator_rejects_task_count_limit()
    test_validator_rejects_cost_budget()
    print("PASS: 3I-C coordinator routing and plan policy validation succeeded.")


if __name__ == "__main__":
    main()

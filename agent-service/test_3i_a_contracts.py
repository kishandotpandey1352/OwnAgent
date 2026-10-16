from decimal import Decimal

from pydantic import ValidationError

from app.agents.contracts import (
    AgentError,
    AgentEvidence,
    AgentName,
    AgentResult,
    AgentStatus,
    AgentTask,
    CalculationLineage,
    CoordinatorPlan,
    EvidenceSource,
    EvidenceSourceType,
)


def _assert_raises(expected_exception, callback) -> None:
    try:
        callback()
    except expected_exception:
        return
    raise AssertionError(
        f"Expected {expected_exception.__name__} was not raised."
    )


def test_contracts_reject_unknown_fields() -> None:
    _assert_raises(
        ValidationError,
        lambda: AgentTask(
            task_id="task-doc",
            request_id="request-1",
            agent_name=AgentName.document_agent,
            instruction="Search selected documents.",
            timeout_seconds=20,
            retry_limit=1,
            estimated_cost_limit_usd=0.01,
            unexpected=True,
        ),
    )


def test_task_rejects_self_dependency() -> None:
    _assert_raises(
        ValidationError,
        lambda: AgentTask(
            task_id="task-doc",
            request_id="request-1",
            agent_name=AgentName.document_agent,
            instruction="Search selected documents.",
            dependencies=["task-doc"],
            timeout_seconds=20,
            retry_limit=1,
            estimated_cost_limit_usd=0.01,
        ),
    )


def test_plan_rejects_unknown_dependency() -> None:
    task = AgentTask(
        task_id="task-calc",
        request_id="request-1",
        agent_name=AgentName.calculation_agent,
        instruction="Calculate growth.",
        dependencies=["missing-task"],
        timeout_seconds=10,
        retry_limit=0,
        estimated_cost_limit_usd=0.0,
    )

    _assert_raises(
        ValidationError,
        lambda: CoordinatorPlan(
            plan_id="plan-1",
            request_id="request-1",
            tasks=[task],
            coordinator_version="3i-coordinator.v1",
            estimated_cost_limit_usd=0.10,
        ),
    )


def test_plan_accepts_valid_dependency_shape() -> None:
    document_task = AgentTask(
        task_id="task-doc",
        request_id="request-1",
        agent_name=AgentName.document_agent,
        instruction="Search selected documents.",
        timeout_seconds=20,
        retry_limit=1,
        estimated_cost_limit_usd=0.01,
    )
    calculation_task = AgentTask(
        task_id="task-calc",
        request_id="request-1",
        agent_name=AgentName.calculation_agent,
        instruction="Calculate using retrieved evidence.",
        dependencies=["task-doc"],
        timeout_seconds=10,
        retry_limit=0,
        estimated_cost_limit_usd=0.0,
    )

    plan = CoordinatorPlan(
        plan_id="plan-1",
        request_id="request-1",
        tasks=[document_task, calculation_task],
        coordinator_version="3i-coordinator.v1",
        estimated_cost_limit_usd=0.10,
    )
    assert len(plan.tasks) == 2
    assert plan.schema_version == "CoordinatorPlan.v1"


def test_calculation_evidence_requires_lineage() -> None:
    source = EvidenceSource(
        source_type=EvidenceSourceType.calculation,
        source_id="calc-1",
    )

    _assert_raises(
        ValidationError,
        lambda: AgentEvidence(
            evidence_id="evidence-calc-1",
            source_agent=AgentName.calculation_agent,
            source=source,
            metric="operating_margin",
            raw_value="22%",
            normalized_numeric_value=Decimal("0.22"),
        ),
    )

    evidence = AgentEvidence(
        evidence_id="evidence-calc-1",
        source_agent=AgentName.calculation_agent,
        source=source,
        metric="operating_margin",
        raw_value="22%",
        normalized_numeric_value=Decimal("0.22"),
        calculation_lineage=CalculationLineage(
            formula="operating_income / revenue",
            input_evidence_ids=["evidence-income", "evidence-revenue"],
        ),
    )
    assert evidence.calculation_lineage is not None


def test_failed_result_requires_structured_error() -> None:
    _assert_raises(
        ValidationError,
        lambda: AgentResult(
            task_id="task-web",
            request_id="request-1",
            agent_name=AgentName.web_research_agent,
            status=AgentStatus.failed,
        ),
    )

    result = AgentResult(
        task_id="task-web",
        request_id="request-1",
        agent_name=AgentName.web_research_agent,
        status=AgentStatus.failed,
        error=AgentError(
            code="WEB_PROVIDER_FAILURE",
            message="Public web research could not be completed.",
            retryable=True,
        ),
    )
    assert result.error is not None
    assert result.error.retryable is True


def main() -> None:
    test_contracts_reject_unknown_fields()
    test_task_rejects_self_dependency()
    test_plan_rejects_unknown_dependency()
    test_plan_accepts_valid_dependency_shape()
    test_calculation_evidence_requires_lineage()
    test_failed_result_requires_structured_error()
    print("PASS: 3I-A versioned agent contracts validated.")


if __name__ == "__main__":
    main()

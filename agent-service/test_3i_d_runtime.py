from __future__ import annotations

import asyncio
import threading
import time

from app.agents.contracts import (
    AgentError,
    AgentName,
    AgentRequest,
    AgentResult,
    AgentStatus,
    AgentTask,
    CoordinatorPlan,
    ExecutionContext,
    ExecutionLimits,
)
from app.agents.registry import get_agent_definition
from app.agents.runtime import DAGExecutor, DAGExecutionStatus


def limits(**overrides) -> ExecutionLimits:
    payload = dict(
        max_agent_count=6,
        max_coordinator_rounds=2,
        max_retries_per_agent=1,
        max_graph_depth=4,
        max_web_searches=2,
        max_web_fetches=8,
        request_timeout_seconds=2.0,
        max_concurrency=2,
        max_llm_tokens=24000,
        max_estimated_cost_usd=0.50,
    )
    payload.update(overrides)
    return ExecutionLimits(**payload)


def context(**overrides) -> ExecutionContext:
    payload = dict(
        request_id="req-3id",
        user_id="local-demo-user",
        use_documents=True,
        document_ids=["doc-1"],
        top_k=6,
        dataset_id="dataset-1",
        allow_web_fallback=True,
        trusted_web_domains=["sec.gov"],
        limits=limits(),
    )
    payload.update(overrides)
    return ExecutionContext(**payload)


def request(**overrides) -> AgentRequest:
    payload = dict(
        request_id="req-3id",
        user_id="local-demo-user",
        question="Test execution",
        use_documents=True,
        document_ids=["doc-1"],
        dataset_id="dataset-1",
        allow_web_fallback=True,
        trusted_web_domains=["sec.gov"],
        metadata={},
    )
    payload.update(overrides)
    return AgentRequest(**payload)


def task(
    task_id: str,
    agent_name: AgentName,
    *,
    dependencies=None,
    required=True,
    timeout_seconds=None,
    retry_limit=None,
    instruction=None,
) -> AgentTask:
    definition = get_agent_definition(agent_name)
    return AgentTask(
        task_id=task_id,
        request_id="req-3id",
        agent_name=agent_name,
        instruction=instruction or f"Execute {task_id}",
        dependencies=list(dependencies or []),
        required=required,
        timeout_seconds=(
            timeout_seconds
            if timeout_seconds is not None
            else min(1.0, definition.timeout_seconds)
        ),
        retry_limit=(
            retry_limit
            if retry_limit is not None
            else min(1, definition.retry_limit)
        ),
        estimated_cost_limit_usd=min(
            0.01,
            definition.estimated_cost_limit_usd,
        ),
    )


def plan(tasks: list[AgentTask]) -> CoordinatorPlan:
    return CoordinatorPlan(
        plan_id="plan-3id",
        request_id="req-3id",
        tasks=tasks,
        coordinator_version="test-3id",
        estimated_cost_limit_usd=sum(
            item.estimated_cost_limit_usd for item in tasks
        ),
    )


class FakeAgent:
    def __init__(
        self,
        agent_name: AgentName,
        *,
        behavior: str = "success",
        sleep_seconds: float = 0.0,
        concurrency=None,
    ):
        self.agent_name = agent_name
        self.behavior = behavior
        self.sleep_seconds = sleep_seconds
        self.calls = 0
        self.concurrency = concurrency

    def execute(self, *, task, context, agent_input):
        self.calls += 1
        if self.concurrency is not None:
            lock, active, peak = self.concurrency
            with lock:
                active[0] += 1
                peak[0] = max(peak[0], active[0])
        try:
            if self.sleep_seconds:
                time.sleep(self.sleep_seconds)

            if self.behavior == "retry_then_success" and self.calls == 1:
                return AgentResult(
                    task_id=task.task_id,
                    request_id=task.request_id,
                    agent_name=task.agent_name,
                    status=AgentStatus.failed,
                    error=AgentError(
                        code="TRANSIENT",
                        message="temporary",
                        retryable=True,
                    ),
                )
            if self.behavior == "permanent_failure":
                return AgentResult(
                    task_id=task.task_id,
                    request_id=task.request_id,
                    agent_name=task.agent_name,
                    status=AgentStatus.failed,
                    error=AgentError(
                        code="PERMANENT",
                        message="permanent",
                        retryable=False,
                    ),
                )
            return AgentResult(
                task_id=task.task_id,
                request_id=task.request_id,
                agent_name=task.agent_name,
                status=AgentStatus.completed,
            )
        finally:
            if self.concurrency is not None:
                lock, active, peak = self.concurrency
                with lock:
                    active[0] -= 1


def resolver(**kwargs):
    return object()


def run(executor, p, *, ctx=None, req=None):
    return asyncio.run(
        executor.execute(
            plan=p,
            request=req or request(),
            context=ctx or context(),
        )
    )


def test_dependency_order_and_parallelism() -> None:
    lock = threading.Lock()
    active = [0]
    peak = [0]
    agents = {
        AgentName.document_agent: FakeAgent(
            AgentName.document_agent,
            sleep_seconds=0.08,
            concurrency=(lock, active, peak),
        ),
        AgentName.web_research_agent: FakeAgent(
            AgentName.web_research_agent,
            sleep_seconds=0.08,
            concurrency=(lock, active, peak),
        ),
        AgentName.calculation_agent: FakeAgent(
            AgentName.calculation_agent,
            concurrency=(lock, active, peak),
        ),
    }
    executor = DAGExecutor(
        agent_getter=lambda name: agents[name],
        input_resolver=resolver,
    )
    p = plan([
        task("doc", AgentName.document_agent),
        task("web", AgentName.web_research_agent, required=False),
        task(
            "calc",
            AgentName.calculation_agent,
            dependencies=["doc", "web"],
        ),
    ])
    result = run(executor, p)
    assert result.status == DAGExecutionStatus.completed
    assert peak[0] == 2
    assert result.execution_order.index("calc") > result.execution_order.index("doc")
    assert result.execution_order.index("calc") > result.execution_order.index("web")


def test_retryable_failure_retries_once() -> None:
    agent = FakeAgent(
        AgentName.document_agent,
        behavior="retry_then_success",
    )
    executor = DAGExecutor(
        agent_getter=lambda _: agent,
        input_resolver=resolver,
    )
    result = run(
        executor,
        plan([task("doc", AgentName.document_agent, retry_limit=1)]),
    )
    assert result.status == DAGExecutionStatus.completed
    assert result.attempts_by_task["doc"] == 2
    assert agent.calls == 2


def test_permanent_failure_does_not_retry() -> None:
    agent = FakeAgent(
        AgentName.document_agent,
        behavior="permanent_failure",
    )
    executor = DAGExecutor(
        agent_getter=lambda _: agent,
        input_resolver=resolver,
    )
    result = run(
        executor,
        plan([task("doc", AgentName.document_agent, retry_limit=1)]),
    )
    assert result.status == DAGExecutionStatus.failed
    assert result.attempts_by_task["doc"] == 1
    assert agent.calls == 1


def test_required_dependency_failure_skips_child() -> None:
    agents = {
        AgentName.document_agent: FakeAgent(
            AgentName.document_agent,
            behavior="permanent_failure",
        ),
        AgentName.calculation_agent: FakeAgent(
            AgentName.calculation_agent,
        ),
    }
    executor = DAGExecutor(
        agent_getter=lambda name: agents[name],
        input_resolver=resolver,
    )
    p = plan([
        task("doc", AgentName.document_agent),
        task(
            "calc",
            AgentName.calculation_agent,
            dependencies=["doc"],
        ),
    ])
    result = run(executor, p)
    by_id = {item.task_id: item for item in result.results}
    assert by_id["calc"].status == AgentStatus.skipped
    assert agents[AgentName.calculation_agent].calls == 0
    assert result.status == DAGExecutionStatus.failed


def test_optional_dependency_failure_does_not_block_child() -> None:
    agents = {
        AgentName.web_research_agent: FakeAgent(
            AgentName.web_research_agent,
            behavior="permanent_failure",
        ),
        AgentName.calculation_agent: FakeAgent(
            AgentName.calculation_agent,
        ),
    }
    executor = DAGExecutor(
        agent_getter=lambda name: agents[name],
        input_resolver=resolver,
    )
    p = plan([
        task("web", AgentName.web_research_agent, required=False),
        task(
            "calc",
            AgentName.calculation_agent,
            dependencies=["web"],
        ),
    ])
    result = run(executor, p)
    by_id = {item.task_id: item for item in result.results}
    assert by_id["web"].status == AgentStatus.failed
    assert by_id["calc"].status == AgentStatus.completed
    assert result.status == DAGExecutionStatus.partial


def test_task_timeout_is_contained() -> None:
    agent = FakeAgent(
        AgentName.document_agent,
        sleep_seconds=0.15,
    )
    executor = DAGExecutor(
        agent_getter=lambda _: agent,
        input_resolver=resolver,
    )
    result = run(
        executor,
        plan([
            task(
                "doc",
                AgentName.document_agent,
                timeout_seconds=0.05,
                retry_limit=0,
            )
        ]),
    )
    assert result.results[0].status == AgentStatus.timed_out
    assert result.status == DAGExecutionStatus.failed


def test_request_timeout_marks_unfinished_tasks() -> None:
    agent = FakeAgent(
        AgentName.document_agent,
        sleep_seconds=0.25,
    )
    executor = DAGExecutor(
        agent_getter=lambda _: agent,
        input_resolver=resolver,
    )
    ctx = context(
        limits=limits(
            request_timeout_seconds=0.05,
            max_concurrency=1,
        )
    )
    result = run(
        executor,
        plan([
            task(
                "doc",
                AgentName.document_agent,
                timeout_seconds=0.5,
            )
        ]),
        ctx=ctx,
    )
    assert result.status == DAGExecutionStatus.timed_out
    assert result.results[0].status == AgentStatus.timed_out


def test_exact_duplicate_tasks_are_suppressed() -> None:
    agent = FakeAgent(AgentName.document_agent)
    executor = DAGExecutor(
        agent_getter=lambda _: agent,
        input_resolver=resolver,
    )
    p = plan([
        task(
            "doc-a",
            AgentName.document_agent,
            instruction="same search",
        ),
        task(
            "doc-b",
            AgentName.document_agent,
            instruction="same search",
        ),
    ])
    result = run(executor, p)
    by_id = {item.task_id: item for item in result.results}
    assert by_id["doc-a"].status == AgentStatus.completed
    assert by_id["doc-b"].status == AgentStatus.skipped
    assert by_id["doc-b"].metadata["duplicate_of"] == "doc-a"
    assert agent.calls == 1
    assert result.status == DAGExecutionStatus.completed


def test_real_input_resolver_direct_calculation() -> None:
    # Uses the real resolver but a fake agent, proving 3I-C direct calculations
    # can be converted into a strict 3I-B CalculationAgentInput.
    captured = {}

    class CapturingAgent(FakeAgent):
        def execute(self, *, task, context, agent_input):
            captured["input"] = agent_input
            return super().execute(
                task=task,
                context=context,
                agent_input=agent_input,
            )

    agent = CapturingAgent(AgentName.calculation_agent)
    executor = DAGExecutor(
        agent_getter=lambda _: agent,
    )
    req = request(
        question="Calculate growth from 100 to 110.",
        use_documents=False,
        document_ids=[],
        dataset_id=None,
        allow_web_fallback=False,
        trusted_web_domains=[],
    )
    ctx = context(
        use_documents=False,
        document_ids=[],
        dataset_id=None,
        allow_web_fallback=False,
        trusted_web_domains=[],
    )
    p = plan([
        task(
            "calc",
            AgentName.calculation_agent,
        )
    ])
    result = run(executor, p, ctx=ctx, req=req)
    assert result.status == DAGExecutionStatus.completed
    calc = captured["input"].calculation
    assert float(calc.previous_value) == 100.0
    assert float(calc.current_value) == 110.0


def main() -> None:
    test_dependency_order_and_parallelism()
    test_retryable_failure_retries_once()
    test_permanent_failure_does_not_retry()
    test_required_dependency_failure_skips_child()
    test_optional_dependency_failure_does_not_block_child()
    test_task_timeout_is_contained()
    test_request_timeout_marks_unfinished_tasks()
    test_exact_duplicate_tasks_are_suppressed()
    test_real_input_resolver_direct_calculation()
    print("PASS: 3I-D bounded DAG runtime, parallelism, retries, and failure semantics validated.")


if __name__ == "__main__":
    main()

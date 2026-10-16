from __future__ import annotations

import asyncio
from collections import defaultdict
from datetime import datetime, timezone
from time import perf_counter
from typing import Callable

from app.agents.contracts import (
    AgentError,
    AgentRequest,
    AgentResult,
    AgentStatus,
    AgentTask,
    CoordinatorPlan,
    ExecutionContext,
)
from app.agents.coordinator.validator import validate_coordinator_plan
from app.agents.runtime.inputs import (
    SpecialistInputResolutionError,
    resolve_specialist_input,
)
from app.agents.runtime.models import (
    DAGExecutionResult,
    DAGExecutionStatus,
)
from app.agents.specialists.factory import get_specialist_agent


AgentGetter = Callable[[object], object]
InputResolver = Callable[..., object]


def _terminal_success(result: AgentResult) -> bool:
    return result.status in {AgentStatus.completed, AgentStatus.partial}


def _skipped_result(
    task: AgentTask,
    *,
    warning: str,
    metadata: dict | None = None,
) -> AgentResult:
    return AgentResult(
        task_id=task.task_id,
        request_id=task.request_id,
        agent_name=task.agent_name,
        status=AgentStatus.skipped,
        evidence=[],
        warnings=[warning],
        estimated_cost_usd=0.0,
        metadata=metadata or {},
    )


def _failure_result(
    task: AgentTask,
    *,
    code: str,
    message: str,
    retryable: bool = False,
) -> AgentResult:
    return AgentResult(
        task_id=task.task_id,
        request_id=task.request_id,
        agent_name=task.agent_name,
        status=AgentStatus.failed,
        evidence=[],
        warnings=[],
        error=AgentError(
            code=code,
            message=message,
            retryable=retryable,
        ),
        estimated_cost_usd=0.0,
    )


def _timed_out_result(
    task: AgentTask,
    *,
    message: str,
) -> AgentResult:
    return AgentResult(
        task_id=task.task_id,
        request_id=task.request_id,
        agent_name=task.agent_name,
        status=AgentStatus.timed_out,
        evidence=[],
        warnings=[],
        error=AgentError(
            code="AGENT_TIMEOUT",
            message=message,
            retryable=True,
        ),
        estimated_cost_usd=0.0,
    )


def _duplicate_aliases(plan: CoordinatorPlan) -> dict[str, str]:
    """Suppress exact duplicate tasks while preserving dependency semantics."""
    seen: dict[tuple, str] = {}
    aliases: dict[str, str] = {}
    for task in plan.tasks:
        signature = (
            task.agent_name.value,
            " ".join(task.instruction.lower().split()),
            tuple(task.dependencies),
        )
        original = seen.get(signature)
        if original is None:
            seen[signature] = task.task_id
        else:
            aliases[task.task_id] = original
    return aliases


class DAGExecutor:
    """Phase 3I-D bounded dependency-aware specialist runtime.

    The runtime:
    - revalidates the coordinator plan before execution,
    - executes independent DAG tasks concurrently,
    - enforces max_concurrency,
    - retries only retryable failures within task policy,
    - treats required dependency failures as blockers,
    - allows optional dependency failures to degrade without blocking,
    - applies task and request timeouts,
    - suppresses exact duplicate tasks,
    - returns typed AgentResult objects.

    Synchronous 3I-B tools are executed with asyncio.to_thread(). Python cannot
    forcibly terminate an already-running worker thread, so timeout cancellation
    is best-effort at this layer; the underlying tools must keep their own
    network/database timeouts, as the existing 3H pipeline already does.
    """

    version = "3I-D.1.0.0"

    def __init__(
        self,
        *,
        agent_getter: AgentGetter = get_specialist_agent,
        input_resolver: InputResolver = resolve_specialist_input,
    ) -> None:
        self._agent_getter = agent_getter
        self._input_resolver = input_resolver

    async def _execute_one(
        self,
        *,
        task: AgentTask,
        request: AgentRequest,
        context: ExecutionContext,
        dependency_results: list[AgentResult],
        semaphore: asyncio.Semaphore,
    ) -> tuple[AgentResult, int]:
        try:
            agent_input = self._input_resolver(
                task=task,
                request=request,
                context=context,
                dependency_results=dependency_results,
            )
        except SpecialistInputResolutionError as exc:
            return (
                _failure_result(
                    task,
                    code="AGENT_INPUT_UNRESOLVED",
                    message=str(exc),
                    retryable=False,
                ),
                0,
            )
        except Exception:
            return (
                _failure_result(
                    task,
                    code="AGENT_INPUT_RESOLUTION_FAILURE",
                    message="The runtime could not resolve a safe specialist input.",
                    retryable=False,
                ),
                0,
            )

        dependency_evidence_ids = [
            evidence.evidence_id
            for result in dependency_results
            if _terminal_success(result)
            for evidence in result.evidence
        ]
        runtime_task = task.model_copy(
            update={"input_evidence_ids": dependency_evidence_ids}
        )

        max_attempts = 1 + min(
            task.retry_limit,
            context.limits.max_retries_per_agent,
        )
        attempts = 0
        loop = asyncio.get_running_loop()
        deadline = loop.time() + task.timeout_seconds

        async with semaphore:
            while attempts < max_attempts:
                remaining = deadline - loop.time()
                if remaining <= 0:
                    return (
                        _timed_out_result(
                            runtime_task,
                            message="The specialist task exceeded its configured timeout.",
                        ),
                        attempts,
                    )

                attempts += 1
                try:
                    agent = self._agent_getter(runtime_task.agent_name)
                    result: AgentResult = await asyncio.wait_for(
                        asyncio.to_thread(
                            agent.execute,
                            task=runtime_task,
                            context=context,
                            agent_input=agent_input,
                        ),
                        timeout=remaining,
                    )
                except asyncio.TimeoutError:
                    return (
                        _timed_out_result(
                            runtime_task,
                            message="The specialist task exceeded its configured timeout.",
                        ),
                        attempts,
                    )
                except Exception:
                    result = _failure_result(
                        runtime_task,
                        code="AGENT_RUNTIME_FAILURE",
                        message="The specialist runtime could not complete the task.",
                        retryable=True,
                    )

                if result.status not in {AgentStatus.failed, AgentStatus.timed_out}:
                    return result, attempts

                if result.error is None or not result.error.retryable:
                    return result, attempts

                if attempts >= max_attempts:
                    return result, attempts

            return (
                _failure_result(
                    runtime_task,
                    code="AGENT_RETRY_EXHAUSTED",
                    message="The specialist task exhausted its retry policy.",
                    retryable=False,
                ),
                attempts,
            )

    async def execute(
        self,
        *,
        plan: CoordinatorPlan,
        request: AgentRequest,
        context: ExecutionContext,
    ) -> DAGExecutionResult:
        if request.request_id != plan.request_id:
            raise ValueError("AgentRequest request_id does not match CoordinatorPlan.")
        if request.request_id != context.request_id:
            raise ValueError("AgentRequest request_id does not match ExecutionContext.")
        if request.user_id != context.user_id:
            raise ValueError("AgentRequest user_id does not match ExecutionContext.")

        validate_coordinator_plan(plan, context)

        started_at = datetime.now(timezone.utc)
        started_clock = perf_counter()
        tasks_by_id = {task.task_id: task for task in plan.tasks}
        results: dict[str, AgentResult] = {}
        attempts_by_task: dict[str, int] = {}
        execution_order: list[str] = []
        warnings: list[str] = []

        duplicate_of = _duplicate_aliases(plan)
        for duplicate_id, original_id in duplicate_of.items():
            duplicate_task = tasks_by_id[duplicate_id]
            results[duplicate_id] = _skipped_result(
                duplicate_task,
                warning=f"Duplicate task suppressed; equivalent task is {original_id}.",
                metadata={"duplicate_of": original_id},
            )
            attempts_by_task[duplicate_id] = 0
            execution_order.append(duplicate_id)

        semaphore = asyncio.Semaphore(context.limits.max_concurrency)

        def resolved_dependency_result(dependency_id: str) -> AgentResult | None:
            result = results.get(dependency_id)
            if result is None:
                return None
            alias = result.metadata.get("duplicate_of")
            if result.status == AgentStatus.skipped and isinstance(alias, str):
                return results.get(alias)
            return result

        def dependency_results_for(task: AgentTask) -> list[AgentResult]:
            collected: list[AgentResult] = []
            for dep_id in task.dependencies:
                resolved = resolved_dependency_result(dep_id)
                if resolved is not None:
                    collected.append(resolved)
            return collected

        def required_dependency_failed(task: AgentTask) -> str | None:
            for dep_id in task.dependencies:
                dependency_task = tasks_by_id[dep_id]
                dependency_result = resolved_dependency_result(dep_id)
                if dependency_result is None:
                    continue
                if dependency_task.required and not _terminal_success(dependency_result):
                    return dep_id
            return None

        async def run_graph() -> None:
            pending = {
                task.task_id
                for task in plan.tasks
                if task.task_id not in results
            }

            while pending:
                ready = [
                    task_id
                    for task_id in pending
                    if all(dep_id in results for dep_id in tasks_by_id[task_id].dependencies)
                ]

                if not ready:
                    # This should be unreachable after 3I-C cycle validation.
                    for task_id in sorted(pending):
                        task = tasks_by_id[task_id]
                        results[task_id] = _failure_result(
                            task,
                            code="DAG_DEADLOCK",
                            message="The runtime could not resolve task dependencies.",
                            retryable=False,
                        )
                        attempts_by_task[task_id] = 0
                        execution_order.append(task_id)
                    pending.clear()
                    return

                runnable: list[str] = []
                for task_id in ready:
                    task = tasks_by_id[task_id]
                    blocker = required_dependency_failed(task)
                    if blocker is not None:
                        results[task_id] = _skipped_result(
                            task,
                            warning=(
                                "Task skipped because required dependency "
                                f"{blocker} did not complete successfully."
                            ),
                            metadata={"blocked_by": blocker},
                        )
                        attempts_by_task[task_id] = 0
                        execution_order.append(task_id)
                        pending.remove(task_id)
                    else:
                        runnable.append(task_id)

                if not runnable:
                    continue

                coroutines = [
                    self._execute_one(
                        task=tasks_by_id[task_id],
                        request=request,
                        context=context,
                        dependency_results=dependency_results_for(
                            tasks_by_id[task_id]
                        ),
                        semaphore=semaphore,
                    )
                    for task_id in runnable
                ]
                outputs = await asyncio.gather(*coroutines)

                for task_id, (result, attempts) in zip(runnable, outputs):
                    results[task_id] = result
                    attempts_by_task[task_id] = attempts
                    execution_order.append(task_id)
                    pending.remove(task_id)

        request_timed_out = False
        try:
            await asyncio.wait_for(
                run_graph(),
                timeout=context.limits.request_timeout_seconds,
            )
        except asyncio.TimeoutError:
            request_timed_out = True
            warnings.append(
                "The multi-agent request exceeded the configured request timeout."
            )
            for task in plan.tasks:
                if task.task_id not in results:
                    results[task.task_id] = _timed_out_result(
                        task,
                        message="The request-level execution timeout was reached.",
                    )
                    attempts_by_task.setdefault(task.task_id, 0)
                    execution_order.append(task.task_id)

        ordered_results = [
            results[task.task_id]
            for task in plan.tasks
            if task.task_id in results
        ]

        if request_timed_out:
            status = DAGExecutionStatus.timed_out
        else:
            def effective_success(task_id: str) -> bool:
                """Treat an intentionally suppressed duplicate as satisfied
                when its canonical task completed successfully/partially."""
                result = results[task_id]
                if _terminal_success(result):
                    return True

                alias = result.metadata.get("duplicate_of")
                if result.status == AgentStatus.skipped and isinstance(alias, str):
                    original = results.get(alias)
                    return original is not None and _terminal_success(original)

                return False

            required_bad = any(
                task.required and not effective_success(task.task_id)
                for task in plan.tasks
            )
            any_degraded = any(
                not effective_success(task.task_id)
                for task in plan.tasks
            )

            if required_bad:
                status = DAGExecutionStatus.failed
            elif any_degraded:
                status = DAGExecutionStatus.partial
            else:
                status = DAGExecutionStatus.completed

        return DAGExecutionResult(
            plan_id=plan.plan_id,
            request_id=plan.request_id,
            status=status,
            results=ordered_results,
            attempts_by_task=attempts_by_task,
            execution_order=execution_order,
            warnings=warnings,
            started_at=started_at,
            latency_ms=max(0, int((perf_counter() - started_clock) * 1000)),
        )


async def execute_coordinator_plan(
    *,
    plan: CoordinatorPlan,
    request: AgentRequest,
    context: ExecutionContext,
) -> DAGExecutionResult:
    return await DAGExecutor().execute(
        plan=plan,
        request=request,
        context=context,
    )

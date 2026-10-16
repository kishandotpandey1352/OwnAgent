from __future__ import annotations

from collections import defaultdict, deque

from app.agents.contracts import AgentName, CoordinatorPlan, ExecutionContext
from app.agents.registry import get_agent_definition, is_registered_agent
from app.agents.specialists.factory import SPECIALIST_AGENTS


class CoordinatorPlanValidationError(ValueError):
    """Raised when a coordinator plan violates a server-owned execution policy."""


def _graph_depth(plan: CoordinatorPlan) -> int:
    """Return longest dependency-chain depth. Raises on cycles."""
    tasks = {task.task_id: task for task in plan.tasks}
    indegree = {task_id: 0 for task_id in tasks}
    children: dict[str, list[str]] = defaultdict(list)

    for task in plan.tasks:
        for dependency in task.dependencies:
            indegree[task.task_id] += 1
            children[dependency].append(task.task_id)

    queue: deque[tuple[str, int]] = deque(
        (task_id, 1) for task_id, degree in indegree.items() if degree == 0
    )
    visited = 0
    max_depth = 0

    while queue:
        task_id, depth = queue.popleft()
        visited += 1
        max_depth = max(max_depth, depth)
        for child in children.get(task_id, []):
            indegree[child] -= 1
            if indegree[child] == 0:
                queue.append((child, depth + 1))

    if visited != len(tasks):
        raise CoordinatorPlanValidationError(
            "Coordinator plan contains a dependency cycle."
        )
    return max_depth


def validate_coordinator_plan(
    plan: CoordinatorPlan,
    context: ExecutionContext,
) -> CoordinatorPlan:
    """Validate a plan against immutable registry policy and request limits.

    This validator is deliberately deterministic and server-owned. The future
    coordinator model may propose a plan; it never gets to approve its own plan.
    """
    if plan.request_id != context.request_id:
        raise CoordinatorPlanValidationError(
            "Coordinator plan request_id does not match the execution context."
        )

    if len(plan.tasks) > context.limits.max_agent_count:
        raise CoordinatorPlanValidationError(
            "Coordinator plan exceeds max_agent_count."
        )

    total_cost = 0.0
    web_task_count = 0

    for task in plan.tasks:
        if not is_registered_agent(task.agent_name):
            raise CoordinatorPlanValidationError(
                f"Unregistered agent in coordinator plan: {task.agent_name.value}."
            )

        # 3I-C may only schedule specialist implementations that actually exist.
        if task.agent_name not in SPECIALIST_AGENTS:
            raise CoordinatorPlanValidationError(
                f"Agent {task.agent_name.value!r} has no executable 3I-B wrapper."
            )

        definition = get_agent_definition(task.agent_name)

        if task.timeout_seconds > definition.timeout_seconds:
            raise CoordinatorPlanValidationError(
                f"Task {task.task_id!r} exceeds the registered agent timeout."
            )
        if task.retry_limit > min(
            definition.retry_limit,
            context.limits.max_retries_per_agent,
        ):
            raise CoordinatorPlanValidationError(
                f"Task {task.task_id!r} exceeds retry policy."
            )
        if task.estimated_cost_limit_usd > definition.estimated_cost_limit_usd:
            raise CoordinatorPlanValidationError(
                f"Task {task.task_id!r} exceeds the registered agent cost limit."
            )

        if definition.document_access and not (
            context.use_documents and context.document_ids
        ):
            raise CoordinatorPlanValidationError(
                f"Task {task.task_id!r} requires document access that is unavailable."
            )

        if definition.dataset_access and not context.dataset_id:
            raise CoordinatorPlanValidationError(
                f"Task {task.task_id!r} requires dataset access that is unavailable."
            )

        if task.agent_name == AgentName.web_research_agent:
            web_task_count += 1
            if not context.allow_web_fallback:
                raise CoordinatorPlanValidationError(
                    "Coordinator plan attempted web research without permission."
                )

        total_cost += task.estimated_cost_limit_usd

    if web_task_count > context.limits.max_web_searches:
        raise CoordinatorPlanValidationError(
            "Coordinator plan exceeds the configured web-search budget."
        )

    if total_cost > context.limits.max_estimated_cost_usd:
        raise CoordinatorPlanValidationError(
            "Coordinator plan exceeds the request cost budget."
        )

    if plan.estimated_cost_limit_usd < total_cost:
        raise CoordinatorPlanValidationError(
            "Coordinator plan cost limit is lower than the sum of task limits."
        )
    if plan.estimated_cost_limit_usd > context.limits.max_estimated_cost_usd:
        raise CoordinatorPlanValidationError(
            "Coordinator plan cost limit exceeds the request budget."
        )

    depth = _graph_depth(plan)
    if depth > context.limits.max_graph_depth:
        raise CoordinatorPlanValidationError(
            "Coordinator plan exceeds max_graph_depth."
        )

    return plan

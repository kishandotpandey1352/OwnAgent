from __future__ import annotations

import re
from dataclasses import dataclass
from uuid import uuid4

from app.agents.contracts import (
    AgentName,
    AgentRequest,
    AgentTask,
    CoordinatorPlan,
    ExecutionContext,
)
from app.agents.coordinator.validator import validate_coordinator_plan
from app.agents.registry import get_agent_definition


COORDINATOR_VERSION = "3I-C.1.0.0"

_NUMBER_PATTERN = re.compile(r"-?\d+(?:\.\d+)?")
_YEAR_PATTERN = re.compile(r"\b20\d{2}\b")

_FINANCIAL_SIGNALS = (
    "revenue",
    "sales",
    "income",
    "earnings",
    "eps",
    "ebitda",
    "cash",
    "debt",
    "asset",
    "liability",
    "equity",
    "margin",
    "ratio",
    "expense",
    "premium",
    "commission",
    "cash flow",
    "capex",
    "free cash flow",
    "kpi",
    "financial metric",
)

_QUANTITATIVE_SIGNALS = (
    "what was",
    "what were",
    "how much",
    "how many",
    "value",
    "amount",
    "trend",
    "compare",
    "comparison",
    "year over year",
    "year-over-year",
    "quarter",
    "annual",
    "extract",
)

_CURRENT_WEB_SIGNALS = (
    "latest",
    "current",
    "today",
    "recent",
    "now",
    "this year",
    "most recent",
    "up to date",
    "up-to-date",
)

_CALCULATION_SIGNALS = (
    "growth",
    "increase",
    "decrease",
    "margin",
    "ratio",
    "difference",
    "delta",
    "change",
    "cagr",
    "percentage",
    "percent",
)

_CHART_SIGNALS = (
    "chart",
    "plot",
    "graph",
    "visualize",
    "visualise",
    "line chart",
    "bar chart",
)


@dataclass(frozen=True)
class RoutingIntent:
    needs_document: bool
    needs_financial_facts: bool
    needs_dataset: bool
    needs_web: bool
    needs_calculation: bool
    needs_chart: bool


def _contains_any(text: str, signals: tuple[str, ...]) -> bool:
    return any(signal in text for signal in signals)


def _classify_request(request: AgentRequest) -> RoutingIntent:
    """Deterministic coordinator routing baseline.

    3I-C intentionally starts with a server-owned deterministic router. A future
    structured-output LLM planner may propose the same plan schema, but the
    validator remains authoritative and unchanged.
    """
    lowered = request.question.lower()
    has_financial_signal = _contains_any(lowered, _FINANCIAL_SIGNALS)
    has_quant_signal = _contains_any(lowered, _QUANTITATIVE_SIGNALS)
    has_year = bool(_YEAR_PATTERN.search(lowered))

    needs_document = bool(request.use_documents and request.document_ids)
    needs_financial_facts = bool(
        needs_document
        and has_financial_signal
        and (has_quant_signal or has_year)
    )

    needs_dataset = bool(request.dataset_id)
    needs_web = bool(
        request.allow_web_fallback
        and _contains_any(lowered, _CURRENT_WEB_SIGNALS)
    )

    # Direct numeric calculations can run immediately. Calculations that depend
    # on retrieved evidence are scheduled after the relevant retrieval tasks.
    numeric_count = len(_NUMBER_PATTERN.findall(request.question))
    calculation_signal = _contains_any(lowered, _CALCULATION_SIGNALS)
    needs_calculation = bool(
        calculation_signal
        and (
            numeric_count >= 2
            or needs_financial_facts
            or needs_web
            or needs_dataset
        )
    )

    needs_chart = bool(
        request.dataset_id
        and (
            _contains_any(lowered, _CHART_SIGNALS)
            or bool(request.metadata.get("chart_request"))
        )
    )

    return RoutingIntent(
        needs_document=needs_document,
        needs_financial_facts=needs_financial_facts,
        needs_dataset=needs_dataset,
        needs_web=needs_web,
        needs_calculation=needs_calculation,
        needs_chart=needs_chart,
    )


def _task(
    *,
    request_id: str,
    agent_name: AgentName,
    instruction: str,
    dependencies: list[str] | None = None,
    required: bool = True,
) -> AgentTask:
    definition = get_agent_definition(agent_name)
    task_id = f"task-{agent_name.value}"
    return AgentTask(
        task_id=task_id,
        request_id=request_id,
        agent_name=agent_name,
        instruction=instruction,
        dependencies=list(dependencies or []),
        required=required,
        timeout_seconds=definition.timeout_seconds,
        retry_limit=definition.retry_limit,
        estimated_cost_limit_usd=definition.estimated_cost_limit_usd,
        metadata={"coordinator_version": COORDINATOR_VERSION},
    )


def build_coordinator_plan(
    request: AgentRequest,
    context: ExecutionContext,
) -> CoordinatorPlan:
    if request.request_id != context.request_id:
        raise ValueError("AgentRequest request_id does not match ExecutionContext.")
    if request.user_id != context.user_id:
        raise ValueError("AgentRequest user_id does not match ExecutionContext.")

    intent = _classify_request(request)
    tasks: list[AgentTask] = []

    source_task_ids: list[str] = []

    if intent.needs_document:
        document_task = _task(
            request_id=request.request_id,
            agent_name=AgentName.document_agent,
            instruction=(
                "Search only the request-scoped uploaded documents for evidence "
                f"relevant to: {request.question}"
            ),
        )
        tasks.append(document_task)
        source_task_ids.append(document_task.task_id)

    if intent.needs_financial_facts:
        fact_dependencies = [
            task.task_id
            for task in tasks
            if task.agent_name == AgentName.document_agent
        ]
        fact_task = _task(
            request_id=request.request_id,
            agent_name=AgentName.financial_fact_agent,
            instruction=(
                "Extract and normalize source-backed financial facts from the "
                f"request-scoped documents for: {request.question}"
            ),
            dependencies=fact_dependencies,
        )
        tasks.append(fact_task)
        source_task_ids.append(fact_task.task_id)

    if intent.needs_dataset:
        data_task = _task(
            request_id=request.request_id,
            agent_name=AgentName.data_analysis_agent,
            instruction=(
                "Profile and analyze only the request-scoped structured dataset "
                f"for: {request.question}"
            ),
        )
        tasks.append(data_task)
        source_task_ids.append(data_task.task_id)

    if intent.needs_web:
        web_task = _task(
            request_id=request.request_id,
            agent_name=AgentName.web_research_agent,
            instruction=(
                "Use the existing controlled 3H web pipeline to obtain current "
                f"public evidence for: {request.question}"
            ),
            required=False,
        )
        tasks.append(web_task)
        source_task_ids.append(web_task.task_id)

    if intent.needs_calculation:
        # Prefer normalized financial facts over raw document chunks when they
        # exist; include web/data evidence when the request needs them.
        calculation_dependencies = [
            task.task_id
            for task in tasks
            if task.agent_name
            in {
                AgentName.financial_fact_agent,
                AgentName.web_research_agent,
                AgentName.data_analysis_agent,
            }
        ]
        calc_task = _task(
            request_id=request.request_id,
            agent_name=AgentName.calculation_agent,
            instruction=(
                "Perform only the deterministic financial calculation required "
                f"by: {request.question}"
            ),
            dependencies=calculation_dependencies,
        )
        tasks.append(calc_task)

    if intent.needs_chart:
        chart_dependencies = [
            task.task_id
            for task in tasks
            if task.agent_name == AgentName.data_analysis_agent
        ]
        chart_task = _task(
            request_id=request.request_id,
            agent_name=AgentName.chart_agent,
            instruction=(
                "Build a validated chart plan from the request-scoped dataset "
                f"for: {request.question}"
            ),
            dependencies=chart_dependencies,
        )
        tasks.append(chart_task)

    # If no specialist is needed, the coordinator does not invent an agent. The
    # caller can continue through the existing conversational answer path until
    # later 3I-E/3I-F stages are available.
    if not tasks:
        raise ValueError(
            "No 3I-C specialist task is required for this request."
        )

    total_cost = sum(task.estimated_cost_limit_usd for task in tasks)
    plan = CoordinatorPlan(
        plan_id=f"plan-{uuid4().hex}",
        request_id=request.request_id,
        tasks=tasks,
        coordinator_version=COORDINATOR_VERSION,
        estimated_cost_limit_usd=total_cost,
        metadata={
            "routing_mode": "deterministic_v1",
            "task_count": len(tasks),
        },
    )
    return validate_coordinator_plan(plan, context)


class Coordinator:
    """Phase 3I-C coordinator facade.

    Planning only: no agent execution, retries, parallelism, reviewer, composer,
    API routing, or frontend activation occurs in 3I-C.
    """

    version = COORDINATOR_VERSION

    def plan(
        self,
        *,
        request: AgentRequest,
        context: ExecutionContext,
    ) -> CoordinatorPlan:
        return build_coordinator_plan(request, context)

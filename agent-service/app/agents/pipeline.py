from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.agents.composition import AnswerComposer, ComposedAnswer
from app.agents.contracts import AgentRequest, CoordinatorPlan, ExecutionContext
from app.agents.coordinator import Coordinator
from app.agents.observability import TraceEvent, TraceSummary, events_from_execution, summarize_trace
from app.agents.review import EvidenceReviewSummary, EvidenceReviewer
from app.agents.runtime import DAGExecutionResult, DAGExecutor
from app.agents.security import BudgetDecision, evaluate_budget, validate_request_context


class MultiAgentPipelineResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "MultiAgentPipelineResult.v1"
    plan: CoordinatorPlan
    execution: DAGExecutionResult
    review: EvidenceReviewSummary
    answer: ComposedAnswer
    pre_execution_budget: BudgetDecision
    post_execution_budget: BudgetDecision
    trace: TraceSummary
    trace_events: list[TraceEvent]


class MultiAgentPipeline:
    """End-to-end governed Phase 3I execution pipeline.

    Planning, validation and specialist execution stay in the existing 3I-C/D
    components. This layer adds the corrected 3I-E reviewer, grounded 3I-F
    composition, 3I-G request/budget controls, and 3I-H trace emission.
    """

    version = "3I-H.1.0.0"

    def __init__(
        self,
        *,
        coordinator: Coordinator | None = None,
        executor: DAGExecutor | None = None,
        reviewer: EvidenceReviewer | None = None,
        composer: AnswerComposer | None = None,
        trace_sink: Callable[[TraceEvent], Any] | None = None,
    ) -> None:
        self.coordinator = coordinator or Coordinator()
        self.executor = executor or DAGExecutor()
        self.reviewer = reviewer or EvidenceReviewer()
        self.composer = composer or AnswerComposer()
        self.trace_sink = trace_sink

    async def run(
        self,
        *,
        request: AgentRequest,
        context: ExecutionContext,
    ) -> MultiAgentPipelineResult:
        security = validate_request_context(request=request, context=context)
        if not security.allowed:
            raise PermissionError(
                "Multi-agent request/context security validation failed: "
                + "; ".join(security.violations)
            )

        plan = self.coordinator.plan(request=request, context=context)
        pre_budget = evaluate_budget(context=context, plan=plan)
        if not pre_budget.allowed:
            raise RuntimeError(
                "Coordinator plan exceeds execution budget: "
                + "; ".join(pre_budget.violations)
            )

        execution = await self.executor.execute(
            plan=plan,
            request=request,
            context=context,
        )
        post_budget = evaluate_budget(context=context, plan=plan, result=execution)

        review = self.reviewer.review(
            request_id=request.request_id,
            agent_results=execution.results,
        )
        if post_budget.allowed:
            answer = self.composer.compose(request=request, review=review)
        else:
            # The specialist work has already happened, so a post-execution
            # overrun cannot be undone. We do, however, stop any optional LLM
            # rendering at this boundary and return only deterministic grounded
            # composition while surfacing the violation.
            answer = AnswerComposer().compose(request=request, review=review)
            answer = answer.model_copy(
                update={
                    "warnings": answer.warnings
                    + [
                        "Execution budget was exceeded; optional post-processing "
                        "was stopped: " + "; ".join(post_budget.violations)
                    ]
                }
            )

        trace_events = events_from_execution(context=context, result=execution)
        if self.trace_sink is not None:
            for event in trace_events:
                self.trace_sink(event)

        return MultiAgentPipelineResult(
            plan=plan,
            execution=execution,
            review=review,
            answer=answer,
            pre_execution_budget=pre_budget,
            post_execution_budget=post_budget,
            trace=summarize_trace(trace_events),
            trace_events=trace_events,
        )

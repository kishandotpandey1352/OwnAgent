from __future__ import annotations

from collections.abc import Callable

from app.agents.contracts import AgentStatus, ExecutionContext
from app.agents.observability.models import TraceEvent, TraceEventType, TraceSummary
from app.agents.runtime.models import DAGExecutionResult, DAGExecutionStatus

TraceSink = Callable[[TraceEvent], None]


class InMemoryTraceCollector:
    def __init__(self) -> None:
        self.events: list[TraceEvent] = []

    def emit(self, event: TraceEvent) -> None:
        self.events.append(event)

    def for_trace(self, trace_id: str) -> list[TraceEvent]:
        return [item for item in self.events if item.trace_id == trace_id]


def events_from_execution(
    *,
    context: ExecutionContext,
    result: DAGExecutionResult,
) -> list[TraceEvent]:
    trace_id = context.trace_id or f"trace-{context.request_id}"
    events: list[TraceEvent] = [
        TraceEvent(
            event_type=TraceEventType.workflow_started,
            trace_id=trace_id,
            request_id=result.request_id,
            plan_id=result.plan_id,
            timestamp=result.started_at,
        )
    ]

    status_map = {
        AgentStatus.completed: TraceEventType.agent_completed,
        AgentStatus.partial: TraceEventType.agent_completed,
        AgentStatus.failed: TraceEventType.agent_failed,
        AgentStatus.timed_out: TraceEventType.agent_timed_out,
        AgentStatus.skipped: TraceEventType.agent_skipped,
    }
    for item in result.results:
        events.append(
            TraceEvent(
                event_type=status_map[item.status],
                trace_id=trace_id,
                request_id=result.request_id,
                plan_id=result.plan_id,
                task_id=item.task_id,
                agent_name=item.agent_name.value,
                timestamp=item.completed_at,
                latency_ms=item.latency_ms,
                token_usage=item.token_usage,
                estimated_cost_usd=item.estimated_cost_usd,
                metadata={
                    "status": item.status.value,
                    "attempts": result.attempts_by_task.get(item.task_id, 0),
                    "error_code": item.error.code if item.error else None,
                },
            )
        )

    final_type = (
        TraceEventType.workflow_completed
        if result.status in {DAGExecutionStatus.completed, DAGExecutionStatus.partial}
        else TraceEventType.workflow_failed
    )
    events.append(
        TraceEvent(
            event_type=final_type,
            trace_id=trace_id,
            request_id=result.request_id,
            plan_id=result.plan_id,
            timestamp=result.completed_at,
            latency_ms=result.latency_ms,
            metadata={"status": result.status.value},
        )
    )
    return events


def summarize_trace(events: list[TraceEvent]) -> TraceSummary:
    if not events:
        raise ValueError("Cannot summarize an empty trace.")
    first = events[0]
    agent_events = [item for item in events if item.task_id]
    workflow_latency = max(
        [item.latency_ms or 0 for item in events if item.event_type in {
            TraceEventType.workflow_completed,
            TraceEventType.workflow_failed,
        }] or [0]
    )
    return TraceSummary(
        trace_id=first.trace_id,
        request_id=first.request_id,
        event_count=len(events),
        agent_count=len(agent_events),
        total_tokens=sum(item.token_usage or 0 for item in agent_events),
        total_estimated_cost_usd=sum(
            item.estimated_cost_usd or 0.0 for item in agent_events
        ),
        workflow_latency_ms=workflow_latency,
    )

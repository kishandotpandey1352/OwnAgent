from __future__ import annotations

from datetime import datetime
from time import perf_counter

from app.agents.contracts import (
    AgentEvidence,
    AgentName,
    AgentResult,
    AgentStatus,
    AgentTask,
    EvidenceSource,
    EvidenceSourceType,
    ExecutionContext,
)
from app.agents.specialist_inputs import ChartAgentInput
from app.agents.specialists.base import SpecialistAgent, SpecialistPolicyError
from app.schemas.tools import ToolName
from app.tools.registry import run_chart_planner


class ChartAgent(SpecialistAgent):
    agent_name = AgentName.chart_agent
    tool_name = ToolName.chart_planner

    def execute(
        self,
        *,
        task: AgentTask,
        context: ExecutionContext,
        agent_input: ChartAgentInput,
    ) -> AgentResult:
        def invoke() -> dict:
            if context.dataset_id is None:
                raise SpecialistPolicyError("No dataset is available in the execution context.")
            if agent_input.request.dataset_id != context.dataset_id:
                raise SpecialistPolicyError(
                    "Chart agent attempted to access a dataset outside the execution context."
                )
            return run_chart_planner(context.user_id, agent_input.request)

        def to_result(output: dict, started_at: datetime, started_clock: float) -> AgentResult:
            chart_payload = {
                "dataset_id": output.get("dataset_id"),
                "file_name": output.get("file_name"),
                "chart_type": output.get("chart_type"),
                "title": output.get("title"),
                "x": output.get("x"),
                "series": output.get("series", []),
                "data": output.get("data", []),
                "source_row_count": output.get("source_row_count"),
                "chart_row_count": output.get("chart_row_count"),
                "sampled": output.get("sampled", False),
                "source_coverage": output.get("source_coverage"),
            }
            evidence = [
                AgentEvidence(
                    evidence_id=f"{task.task_id}:chart:{agent_input.request.dataset_id}",
                    source_agent=self.agent_name,
                    source=EvidenceSource(
                        source_type=EvidenceSourceType.dataset,
                        source_id=agent_input.request.dataset_id,
                        title=output.get("file_name"),
                    ),
                    raw_value=(
                        f"{output.get('chart_type')} chart: {output.get('title')} "
                        f"({output.get('chart_row_count', 0)} rows)"
                    ),
                    confidence=output.get("source_coverage"),
                    snippet=output.get("explanation"),
                    metadata={"chart_spec": chart_payload},
                )
            ]
            return AgentResult(
                task_id=task.task_id,
                request_id=task.request_id,
                agent_name=self.agent_name,
                status=AgentStatus.completed,
                evidence=evidence,
                warnings=[str(item) for item in output.get("warnings", [])],
                latency_ms=max(0, int((perf_counter() - started_clock) * 1000)),
                estimated_cost_usd=0.0,
                started_at=started_at,
                metadata={
                    "agent_version": self.version,
                    "tool_name": self.tool_name.value,
                    "chart_type": output.get("chart_type"),
                },
            )

        return self._execute_guarded(
            task=task,
            context=context,
            invoke=invoke,
            to_result=to_result,
        )

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
from app.agents.specialist_inputs import DataAnalysisAgentInput
from app.agents.specialists.base import SpecialistAgent, SpecialistPolicyError
from app.schemas.tools import CsvProfileInput, ToolName
from app.tools.registry import run_csv_profile


class DataAnalysisAgent(SpecialistAgent):
    agent_name = AgentName.data_analysis_agent
    tool_name = ToolName.csv_profile

    def execute(
        self,
        *,
        task: AgentTask,
        context: ExecutionContext,
        agent_input: DataAnalysisAgentInput,
    ) -> AgentResult:
        def invoke() -> dict:
            if context.dataset_id is None:
                raise SpecialistPolicyError("No dataset is available in the execution context.")
            if agent_input.dataset_id != context.dataset_id:
                raise SpecialistPolicyError(
                    "Data agent attempted to access a dataset outside the execution context."
                )
            return run_csv_profile(
                context.user_id,
                CsvProfileInput(dataset_id=agent_input.dataset_id),
            )

        def to_result(output: dict, started_at: datetime, started_clock: float) -> AgentResult:
            summary = {
                "row_count": output.get("row_count"),
                "column_count": output.get("column_count"),
                "columns": output.get("columns", []),
                "chart_suggestions": output.get("chart_suggestions", []),
            }
            evidence = [
                AgentEvidence(
                    evidence_id=f"{task.task_id}:dataset:{agent_input.dataset_id}",
                    source_agent=self.agent_name,
                    source=EvidenceSource(
                        source_type=EvidenceSourceType.dataset,
                        source_id=agent_input.dataset_id,
                        title=output.get("file_name"),
                    ),
                    raw_value=(
                        f"Dataset profile: {output.get('row_count', 0)} rows, "
                        f"{output.get('column_count', 0)} columns"
                    ),
                    confidence=1.0,
                    snippet=(
                        f"Dataset profile: {output.get('row_count', 0)} rows, "
                        f"{output.get('column_count', 0)} columns."
                    ),
                    metadata={
                        "dataset_profile": summary,
                        "sample_rows": output.get("sample_rows", []),
                    },
                )
            ]
            return AgentResult(
                task_id=task.task_id,
                request_id=task.request_id,
                agent_name=self.agent_name,
                status=AgentStatus.completed,
                evidence=evidence,
                warnings=[],
                latency_ms=max(0, int((perf_counter() - started_clock) * 1000)),
                estimated_cost_usd=0.0,
                started_at=started_at,
                metadata={
                    "agent_version": self.version,
                    "tool_name": self.tool_name.value,
                    "dataset_id": agent_input.dataset_id,
                },
            )

        return self._execute_guarded(
            task=task,
            context=context,
            invoke=invoke,
            to_result=to_result,
        )

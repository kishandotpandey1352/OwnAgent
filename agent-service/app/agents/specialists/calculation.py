from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from time import perf_counter
from typing import Any

from app.agents.contracts import (
    AgentEvidence,
    AgentName,
    AgentResult,
    AgentStatus,
    AgentTask,
    CalculationLineage,
    EvidenceSource,
    EvidenceSourceType,
    ExecutionContext,
)
from app.agents.specialist_inputs import CalculationAgentInput
from app.agents.specialists.base import SpecialistAgent
from app.schemas.tools import ToolName
from app.tools.registry import run_financial_calculator


class CalculationAgent(SpecialistAgent):
    agent_name = AgentName.calculation_agent
    tool_name = ToolName.financial_calculator

    @staticmethod
    def _task_input_evidence(task: AgentTask, values: dict[str, Any]) -> list[AgentEvidence]:
        evidence: list[AgentEvidence] = []
        for key, value in values.items():
            if value is None or key == "calculation_type":
                continue
            evidence_id = f"{task.task_id}:input:{key}"
            evidence.append(
                AgentEvidence(
                    evidence_id=evidence_id,
                    source_agent=AgentName.calculation_agent,
                    source=EvidenceSource(
                        source_type=EvidenceSourceType.system,
                        source_id=evidence_id,
                        title="User/task calculation input",
                    ),
                    metric=key,
                    raw_value=str(value),
                    normalized_numeric_value=Decimal(str(value)),
                    confidence=1.0,
                    metadata={"origin": "task_calculation_input"},
                )
            )
        return evidence

    def execute(
        self,
        *,
        task: AgentTask,
        context: ExecutionContext,
        agent_input: CalculationAgentInput,
    ) -> AgentResult:
        def invoke() -> dict:
            return run_financial_calculator(agent_input.calculation)

        def to_result(output: dict, started_at: datetime, started_clock: float) -> AgentResult:
            if task.input_evidence_ids:
                task_input_evidence: list[AgentEvidence] = []
                lineage_ids = list(task.input_evidence_ids)
            else:
                task_input_evidence = self._task_input_evidence(
                    task,
                    agent_input.calculation.model_dump(mode="python"),
                )
                lineage_ids = [item.evidence_id for item in task_input_evidence]
            result_value = output.get("result_percent")
            unit = "percent" if result_value is not None else None
            if result_value is None:
                result_value = output.get("result")

            calculation_evidence = AgentEvidence(
                evidence_id=f"{task.task_id}:calculation:result",
                source_agent=self.agent_name,
                source=EvidenceSource(
                    source_type=EvidenceSourceType.calculation,
                    source_id=f"calculation:{task.task_id}",
                    title=output.get("calculation_type"),
                ),
                metric=str(output.get("calculation_type")),
                raw_value=str(result_value),
                normalized_numeric_value=(
                    Decimal(str(result_value)) if result_value is not None else None
                ),
                unit=unit,
                confidence=1.0,
                snippet=output.get("explanation"),
                calculation_lineage=CalculationLineage(
                    formula=output.get("explanation") or "Deterministic financial calculation",
                    input_evidence_ids=lineage_ids,
                ),
                metadata={
                    "result": output.get("result"),
                    "result_percent": output.get("result_percent"),
                },
            )
            return AgentResult(
                task_id=task.task_id,
                request_id=task.request_id,
                agent_name=self.agent_name,
                status=AgentStatus.completed,
                evidence=[*task_input_evidence, calculation_evidence],
                warnings=[],
                latency_ms=max(0, int((perf_counter() - started_clock) * 1000)),
                estimated_cost_usd=0.0,
                started_at=started_at,
                metadata={
                    "agent_version": self.version,
                    "tool_name": self.tool_name.value,
                },
            )

        return self._execute_guarded(
            task=task,
            context=context,
            invoke=invoke,
            to_result=to_result,
        )
